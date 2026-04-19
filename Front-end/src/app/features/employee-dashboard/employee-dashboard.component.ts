import { Component, OnInit, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../../core/services/auth.service';
import { ClockifyService } from '../../core/services/clockify.service';
import { CsvService } from '../../core/services/csv.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { saveAs } from 'file-saver';
import { environment } from '../../../environments/environment';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-employee-dashboard',
  templateUrl: './employee-dashboard.component.html',
  styleUrls: ['./employee-dashboard.component.scss']
})
export class EmployeeDashboardComponent implements OnInit, OnDestroy {
  employeeName     = '';
  companyName      = '';
  clockifyUsername = '';

  // Reactive data source — currentUser$ ile güncellenir
  userDataSource: 'csv' | 'clockify' = 'clockify';

  // Clockify
  workspaces: any[]          = [];
  projects: any[]            = [];
  selectedWorkspace          = '';
  selectedProjects: string[] = [];
  startDate: Date | null     = null;
  endDate:   Date | null     = null;
  format                     = 'hours';
  loading                    = false;
  generating                 = false;
  connectionError            = '';

  // CSV
  selectedFile: File | null  = null;
  fileName                   = '';
  csvData: any               = null;
  csvLoading                 = false;
  csvConverting              = false;
  selectedClients: string[]  = [];
  selectedUsers: string[]    = [];

  private userSub?: Subscription;

  constructor(
    private authService: AuthService,
    private clockifyService: ClockifyService,
    private csvService: CsvService,
    private http: HttpClient,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    // currentUser$ — profil güncellenince otomatik tetiklenir
    this.userSub = this.authService.currentUser$.subscribe(user => {
      if (!user) return;

      const p = user.profile as any;
      this.employeeName     = p?.full_name        || user.email;
      this.companyName      = p?.company_name      || '';
      this.clockifyUsername = p?.clockify_username || '';

      const newSource = user.data_source || 'clockify';

      // Kaynak değiştiyse Clockify bağlantısını sıfırla veya yükle
      if (newSource !== this.userDataSource) {
        this.userDataSource = newSource;

        if (newSource === 'clockify' && this.workspaces.length === 0) {
          this.loadWorkspaces();
        }
      } else if (newSource === 'clockify' && this.workspaces.length === 0) {
        this.loadWorkspaces();
      }

      this.userDataSource = newSource;
    });

    // Default: current month
    const now = new Date();
    this.startDate = new Date(now.getFullYear(), now.getMonth(), 1);
    this.endDate   = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  }

  ngOnDestroy(): void {
    this.userSub?.unsubscribe();
  }

  // ── CLOCKIFY ──────────────────────────────────────────

  loadWorkspaces(): void {
    this.loading        = true;
    this.connectionError = '';

    this.clockifyService.getWorkspaces('').subscribe({
      next: (ws) => {
        this.workspaces = ws;
        this.loading    = false;
        if (ws.length > 0) {
          this.selectedWorkspace = ws[0].id;
          this.onWorkspaceChange();
        }
      },
      error: () => {
        this.loading         = false;
        this.connectionError = 'Failed to connect to Clockify. Please contact your employer.';
      }
    });
  }

  onWorkspaceChange(): void {
    if (!this.selectedWorkspace) return;
    this.clockifyService.getProjects('', this.selectedWorkspace).subscribe({
      next: (p) => { this.projects = p; },
      error: () => {}
    });
  }

  private formatDateLocal(date: Date, isEnd: boolean): string {
    const pad  = (n: number) => n.toString().padStart(2, '0');
    const y    = date.getFullYear();
    const mo   = pad(date.getMonth() + 1);
    const d    = pad(date.getDate());
    const time = isEnd ? 'T23:59:59.999Z' : 'T00:00:00.000Z';
    return `${y}-${mo}-${d}${time}`;
  }

  generateReport(): void {
    if (!this.startDate || !this.endDate) {
      this.snackBar.open('Please select start and end dates', 'Close', { duration: 3000 });
      return;
    }

    this.generating = true;

    const payload = {
      workspace_id: this.selectedWorkspace,
      start_date:   this.formatDateLocal(this.startDate, false),
      end_date:     this.formatDateLocal(this.endDate,   true),
      project_ids:  this.selectedProjects,
      format:       this.format
    };

    this.http.post(`${environment.apiUrl}/clockify/employee-report`, payload, { responseType: 'blob' })
      .subscribe({
        next: (blob) => {
          const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
          saveAs(blob, `Report_${this.clockifyUsername}_${ts}.xlsx`);
          this.snackBar.open('Report generated successfully!', 'Close', { duration: 3000 });
          this.generating = false;
        },
        error: async (err) => {
          let msg = 'Error generating report';
          try {
            const text   = await err.error.text();
            const parsed = JSON.parse(text);
            msg = parsed.error || msg;
          } catch {}
          this.snackBar.open(msg, 'Close', { duration: 5000 });
          this.generating = false;
        }
      });
  }

  // ── CSV ───────────────────────────────────────────────

  onFileSelected(event: any): void {
    const file: File = event.target.files[0];
    if (file && file.name.endsWith('.csv')) {
      this.selectedFile = file;
      this.fileName     = file.name;
      this.loadCsvPreview();
    } else {
      this.snackBar.open('Please select a CSV file', 'Close', { duration: 3000 });
    }
  }

  loadCsvPreview(): void {
    if (!this.selectedFile) return;
    this.csvLoading = true;
    this.csvService.previewCsv(this.selectedFile).subscribe({
      next: (data) => {
        this.csvData    = data;
        this.csvLoading = false;
        this.snackBar.open(`Loaded ${data.total_rows} rows`, 'Close', { duration: 2000 });
      },
      error: () => {
        this.snackBar.open('Error loading CSV', 'Close', { duration: 3000 });
        this.csvLoading = false;
      }
    });
  }

  onCsvConvert(): void {
    if (!this.selectedFile) {
      this.snackBar.open('Please select a CSV file', 'Close', { duration: 3000 });
      return;
    }

    this.csvConverting = true;

    const filters = {
      projects: this.selectedProjects.length > 0 ? this.selectedProjects : ['all'],
      clients:  this.selectedClients.length  > 0 ? this.selectedClients  : ['all'],
      users:    this.selectedUsers.length    > 0 ? this.selectedUsers    : ['all'],
      format:   this.format
    };

    this.csvService.convertToExcel(this.selectedFile, filters).subscribe({
      next: (blob) => {
        const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
        saveAs(blob, `Report_${ts}.xlsx`);
        this.snackBar.open('Report generated successfully!', 'Close', { duration: 3000 });
        this.csvConverting = false;
      },
      error: (error) => {
        this.snackBar.open(error.error?.error || 'Error generating report', 'Close', { duration: 5000 });
        this.csvConverting = false;
      }
    });
  }

  removeFile(): void {
    this.selectedFile = null;
    this.fileName     = '';
    this.csvData      = null;
  }
}