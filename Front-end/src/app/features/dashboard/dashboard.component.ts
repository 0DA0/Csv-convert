import { Component, OnInit } from '@angular/core';
import { AuthService } from '../../core/services/auth.service';
import { CsvService } from '../../core/services/csv.service';
import { ClockifyService } from '../../core/services/clockify.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { saveAs } from 'file-saver';

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss']
})
export class DashboardComponent implements OnInit {
  dataSource: 'csv' | 'clockify' = 'csv';
  
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
  clockifyApiKey = '';
  clockifyWorkspaces: any[] = [];
  clockifyProjects: any[] = [];
  selectedWorkspace = '';
  selectedClockifyProjects: string[] = [];
  clockifyStartDate = '';
  clockifyEndDate = '';
  clockifyLoading = false;

  constructor(
    public authService: AuthService,
    private csvService: CsvService,
    private clockifyService: ClockifyService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.loadSavedApiKey();
    this.setDefaultDates();
  }

  selectDataSource(source: 'csv' | 'clockify'): void {
    this.dataSource = source;
  }

  loadSavedApiKey(): void {
    this.clockifyService.getApiKey().subscribe({
      next: (response) => {
        if (response.api_key) {
          this.clockifyApiKey = response.api_key;
        }
      },
      error: () => {}
    });
  }

  setDefaultDates(): void {
    const now = new Date();
    const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
    const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    
    this.clockifyStartDate = firstDay.toISOString().split('T')[0];
    this.clockifyEndDate = lastDay.toISOString().split('T')[0];
  }

  saveClockifyApiKey(): void {
    this.clockifyService.saveApiKey(this.clockifyApiKey).subscribe({
      next: () => {
        this.snackBar.open('API key saved successfully!', 'Close', { duration: 3000 });
      },
      error: () => {
        this.snackBar.open('Failed to save API key', 'Close', { duration: 3000 });
      }
    });
  }

  loadClockifyWorkspaces(): void {
    if (!this.clockifyApiKey) return;

    this.clockifyLoading = true;
    this.clockifyService.getWorkspaces(this.clockifyApiKey).subscribe({
      next: (workspaces) => {
        this.clockifyWorkspaces = workspaces;
        this.clockifyLoading = false;
        this.snackBar.open('Connected to Clockify!', 'Close', { duration: 3000 });
      },
      error: () => {
        this.snackBar.open('Invalid API key or connection failed', 'Close', { duration: 5000 });
        this.clockifyLoading = false;
      }
    });
  }

  onWorkspaceChange(): void {
    if (!this.selectedWorkspace) return;

    this.clockifyService.getProjects(this.clockifyApiKey, this.selectedWorkspace).subscribe({
      next: (projects) => {
        this.clockifyProjects = projects;
      },
      error: () => {
        this.snackBar.open('Failed to load projects', 'Close', { duration: 3000 });
      }
    });
  }

  generateClockifyReport(): void {
    this.converting = true;

    const data = {
      api_key: this.clockifyApiKey,
      workspace_id: this.selectedWorkspace,
      start_date: new Date(this.clockifyStartDate).toISOString(),
      end_date: new Date(this.clockifyEndDate).toISOString(),
      project_ids: this.selectedClockifyProjects,
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
        this.snackBar.open(error.error?.error || 'Error generating report', 'Close', { duration: 5000 });
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

  onFileSelected(event: any): void {const file: File = event.target.files[0];
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