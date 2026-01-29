import { Component, OnInit, OnDestroy } from '@angular/core';
import { AuthService } from '../../core/services/auth.service';
import { CsvService } from '../../core/services/csv.service';
import { ClockifyService } from '../../core/services/clockify.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { saveAs } from 'file-saver';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss']
})
export class DashboardComponent implements OnInit, OnDestroy {
  userDataSource: 'csv' | 'clockify' = 'csv';
  
  // CSV
  selectedFile: File | null = null;
  fileName = '';
  csvData: any = null;
  loading = false;
  converting = false;

  // Filters
  selectedProjects: string[] = [];
  selectedClients: string[] = [];
  selectedUsers: string[] = [];
  format = 'decimal';

  // Clockify
  clockifyWorkspaces: any[] = [];
  clockifyProjects: any[] = [];
  selectedWorkspace = '';
  selectedClockifyProjects: string[] = [];
  clockifyStartDate = '';
  clockifyEndDate = '';
  clockifyLoading = false;
  private hasLoadedWorkspaces = false;
  private hasAttemptedConnection = false;
  private userSubscription?: Subscription;

  constructor(
    public authService: AuthService,
    private csvService: CsvService,
    private clockifyService: ClockifyService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.userSubscription = this.authService.currentUser$.subscribe(user => {
      if (user) {
        this.userDataSource = user.data_source || 'csv';
        
        // Eğer Clockify kullanıcısıysa VE daha önce yüklenmediyse VE API key varsa, otomatik bağlan
        if (this.userDataSource === 'clockify' && !this.hasLoadedWorkspaces && !this.hasAttemptedConnection) {
          this.hasAttemptedConnection = true;
          // Biraz gecikme ile bağlan (sayfa yüklenmesini bekle)
          setTimeout(() => {
            this.loadClockifyWorkspaces();
          }, 500);
        }
      }
    });

    this.setDefaultDates();
  }

  ngOnDestroy(): void {
    if (this.userSubscription) {
      this.userSubscription.unsubscribe();
    }
  }

  setDefaultDates(): void {
    const now = new Date();
    const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
    const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    
    this.clockifyStartDate = firstDay.toISOString().split('T')[0];
    this.clockifyEndDate = lastDay.toISOString().split('T')[0];
  }

  loadClockifyWorkspaces(): void {
    // Eğer zaten yüklenmiş workspace'ler varsa, tekrar yükleme
    if (this.hasLoadedWorkspaces || this.clockifyWorkspaces.length > 0) {
      return;
    }

    // Zaten yükleme yapılıyorsa, tekrar başlatma
    if (this.clockifyLoading) {
      return;
    }

    this.clockifyLoading = true;
    
    this.clockifyService.getWorkspaces('').subscribe({
      next: (workspaces) => {
        this.clockifyWorkspaces = workspaces;
        this.clockifyLoading = false;
        this.hasLoadedWorkspaces = true;
        // Başarılı bağlantı - bildirim yok, sadece yeşil durum göster
      },
      error: (error) => {
        this.clockifyLoading = false;
        
        // Hata durumunda sadece gerçek hatalarda bildirim göster
        // 400 veya 401 hatalarında kullanıcının profile'a gitmesi gerekiyor
        if (error.status === 401 || error.status === 400) {
          // API key problemi - kullanıcıya haber ver
          this.snackBar.open(
            'Clockify connection failed. Please update your API key in Profile settings.', 
            'Go to Profile', 
            { 
              duration: 0,  // Manuel kapatana kadar göster
              horizontalPosition: 'center',
              verticalPosition: 'top'
            }
          ).onAction().subscribe(() => {
            // "Go to Profile" butonuna tıklandığında
            window.location.href = '/profile';
          });
        } else {
          // Diğer hatalar (network vb.)
          console.error('Clockify connection error:', error);
        }
      }
    });
  }

  onWorkspaceChange(): void {
    if (!this.selectedWorkspace) return;

    this.clockifyService.getProjects('', this.selectedWorkspace).subscribe({
      next: (projects) => {
        this.clockifyProjects = projects;
      },
      error: (error) => {
        console.error('Failed to load projects:', error);
        this.snackBar.open('Failed to load projects', 'Close', { duration: 3000 });
      }
    });
  }

  generateClockifyReport(): void {
    this.converting = true;

    const startDate = new Date(this.clockifyStartDate);
    const endDate = new Date(this.clockifyEndDate);
    endDate.setHours(23, 59, 59, 999);

    const data = {
      workspace_id: this.selectedWorkspace,
      start_date: startDate.toISOString(),
      end_date: endDate.toISOString(),
      project_ids: this.selectedClockifyProjects.length > 0 ? this.selectedClockifyProjects : [],
      format: this.format
    };

    this.clockifyService.getTimeEntries(data).subscribe({
      next: (blob) => {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
        saveAs(blob, `Clockify_Report_${timestamp}.xlsx`);
        this.snackBar.open('Report generated successfully!', 'Close', { duration: 3000 });
        this.converting = false;
      },
      error: (error) => {
        let errorMessage = 'Error generating report';
        if (error.error) {
          // Blob hatasını text'e çevir
          const reader = new FileReader();
          reader.onload = () => {
            try {
              const errorObj = JSON.parse(reader.result as string);
              errorMessage = errorObj.error || errorMessage;
            } catch {
              errorMessage = 'Error generating report';
            }
            this.snackBar.open(errorMessage, 'Close', { duration: 5000 });
          };
          reader.readAsText(error.error);
        } else {
          this.snackBar.open(errorMessage, 'Close', { duration: 5000 });
        }
        this.converting = false;
      }
    });
  }

  getUserDisplayName(): string {
    const user = this.authService.getCurrentUser();
    if (!user) return 'Guest';
    
    if (user.user_type === 'company') {
      const profile = user.profile as any;
      return profile.company_name || user.email;
    } else {
      const profile = user.profile as any;
      return profile.full_name || user.email;
    }
  }

  // CSV Methods
  onFileSelected(event: any): void {
    const file: File = event.target.files[0];
    if (file && file.name.endsWith('.csv')) {
      this.selectedFile = file;
      this.fileName = file.name;
      this.loadCsvPreview();
    } else {
      this.snackBar.open('Please select a CSV file', 'Close', { duration: 3000 });
    }
  }

  loadCsvPreview(): void {
    if (!this.selectedFile) return;
    
    this.loading = true;
    this.csvService.previewCsv(this.selectedFile).subscribe({
      next: (data) => {
        this.csvData = data;
        this.loading = false;
        this.snackBar.open(`Loaded ${data.total_rows} rows`, 'Close', { duration: 2000 });
      },
      error: () => {
        this.snackBar.open('Error loading CSV', 'Close', { duration: 3000 });
        this.loading = false;
      }
    });
  }

  onConvert(): void {
    if (!this.selectedFile) {
      this.snackBar.open('Please select a CSV file', 'Close', { duration: 3000 });
      return;
    }

    this.converting = true;

    const filters = {
      projects: this.selectedProjects.length > 0 ? this.selectedProjects : ['all'],
      clients: this.selectedClients.length > 0 ? this.selectedClients : ['all'],
      users: this.selectedUsers.length > 0 ? this.selectedUsers : ['all'],
      format: this.format
    };

    this.csvService.convertToExcel(this.selectedFile, filters).subscribe({
      next: (blob) => {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
        saveAs(blob, `Report_${timestamp}.xlsx`);
        this.snackBar.open('Report generated successfully!', 'Close', { duration: 3000 });
        this.converting = false;
      },
      error: (error) => {
        this.snackBar.open(error.error?.error || 'Error generating report', 'Close', { duration: 5000 });
        this.converting = false;
      }
    });
  }

  removeFile(): void {
    this.selectedFile = null;
    this.fileName = '';
    this.csvData = null;
  }
}