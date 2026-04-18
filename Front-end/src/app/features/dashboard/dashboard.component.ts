import { Component, OnInit, OnDestroy } from '@angular/core';
import { AuthService } from '../../core/services/auth.service';
import { CsvService } from '../../core/services/csv.service';
import { ClockifyService } from '../../core/services/clockify.service';
import { HttpClient } from '@angular/common/http';
import { MatSnackBar } from '@angular/material/snack-bar';
import { saveAs } from 'file-saver';
import { Subscription } from 'rxjs';
import { environment } from '../../../environments/environment';

// Sütunlar kısaltılıyor: CSV'de çok sütun var, sadece önemlileri göster
const CSV_VISIBLE_COLS  = ['Project', 'Client', 'User', 'Description', 'Start Date', 'Start Time', 'End Time', 'Duration (h)', 'Billable'];
const CLOCK_VISIBLE_COLS = ['Project', 'Client', 'User', 'Description', 'Start Date', 'Start Time', 'End Time', 'Duration (h)', 'Billable'];

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
  selectedClients:  string[] = [];
  selectedUsers:    string[] = [];
  format = 'decimal';

  // Clockify
  clockifyWorkspaces:      any[] = [];
  clockifyProjects:        any[] = [];
  selectedWorkspace        = '';
  selectedClockifyProjects: string[] = [];
  clockifyStartDate: Date | null = null;
  clockifyEndDate:   Date | null = null;
  clockifyLoading = false;

  // Clockify preview
  clockifyPreviewData: any = null;
  clockifyPreviewLoading = false;
  clockifyPreviewColumns = CLOCK_VISIBLE_COLS;
  private previewDebounce: any = null;

  private userSubscription?: Subscription;
  private workspacesLoaded = false;

  constructor(
    public authService: AuthService,
    private csvService: CsvService,
    private clockifyService: ClockifyService,
    private http: HttpClient,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.setDefaultDates();

    const user = this.authService.getCurrentUser();
    if (user) {
      this.userDataSource = user.data_source || 'csv';
      if (this.userDataSource === 'clockify') this.loadClockifyWorkspaces();
    } else {
      this.userSubscription = this.authService.currentUser$.subscribe(u => {
        if (u && !this.workspacesLoaded) {
          this.userDataSource = u.data_source || 'csv';
          if (this.userDataSource === 'clockify') this.loadClockifyWorkspaces();
          this.userSubscription?.unsubscribe();
        }
      });
    }
  }

  ngOnDestroy(): void {
    this.userSubscription?.unsubscribe();
    if (this.previewDebounce) clearTimeout(this.previewDebounce);
  }

  setDefaultDates(): void {
    const now = new Date();
    this.clockifyStartDate = new Date(now.getFullYear(), now.getMonth(), 1);
    this.clockifyEndDate   = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  }

  // ── CSV ──────────────────────────────────────────────

  /** Sadece ilgili sütunları göster; CSV'de olmayan sütunları atla */
  getVisibleColumns(): string[] {
    if (!this.csvData?.columns) return [];
    return CSV_VISIBLE_COLS.filter(c => this.csvData.columns.includes(c));
  }

  onFileSelected(event: any): void {
    const file: File = event.target.files[0];
    if (!file?.name.endsWith('.csv')) {
      this.snackBar.open('Please select a CSV file', 'Close', { duration: 3000 });
      return;
    }
    this.selectedFile = file;
    this.fileName     = file.name;
    this.csvData      = null;
    this.loadCsvPreview();
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
      error: (err) => {
        this.snackBar.open(err.error?.error || 'Error loading CSV', 'Close', { duration: 3000 });
        this.loading = false;
      }
    });
  }

  onConvert(): void {
    if (!this.selectedFile) return;
    this.converting = true;
    const filters = {
      projects: this.selectedProjects.length > 0 ? this.selectedProjects : ['all'],
      clients:  this.selectedClients.length  > 0 ? this.selectedClients  : ['all'],
      users:    this.selectedUsers.length    > 0 ? this.selectedUsers    : ['all'],
      format:   this.format
    };
    this.csvService.convertToExcel(this.selectedFile, filters).subscribe({
      next: (blob) => {
        saveAs(blob, `Report_${Date.now()}.xlsx`);
        this.snackBar.open('Report generated!', 'Close', { duration: 3000 });
        this.converting = false;
      },
      error: (err) => {
        this.snackBar.open(err.error?.error || 'Error generating report', 'Close', { duration: 5000 });
        this.converting = false;
      }
    });
  }

  removeFile(): void {
    this.selectedFile = null;
    this.fileName     = '';
    this.csvData      = null;
  }

  // ── Clockify ─────────────────────────────────────────

  loadClockifyWorkspaces(): void {
    if (this.workspacesLoaded || this.clockifyLoading) return;
    this.clockifyLoading = true;
    this.clockifyService.getWorkspaces('').subscribe({
      next: (ws) => {
        this.clockifyWorkspaces = ws;
        this.clockifyLoading    = false;
        this.workspacesLoaded   = true;
        // İlk workspace'i otomatik seç
        if (ws.length > 0) {
          this.selectedWorkspace = ws[0].id;
          this.onWorkspaceChange();
        }
      },
      error: () => {
        this.clockifyLoading = false;
        this.snackBar.open('Failed to connect to Clockify. Check your API key in profile.', 'Close', { duration: 5000 });
      }
    });
  }

  onWorkspaceChange(): void {
    if (!this.selectedWorkspace) return;
    this.clockifyProjects = [];
    this.clockifyService.getProjects('', this.selectedWorkspace).subscribe({
      next: (p) => { this.clockifyProjects = p; },
      error: () => {}
    });
    // Workspace değişince preview'i de güncelle
    this.scheduleClockifyPreview();
  }

  /** Tarih veya proje değişince preview'i debounce ile yükle (1 sn bekle) */
  onClockifyDateChange(): void {
    this.scheduleClockifyPreview();
  }

  private scheduleClockifyPreview(): void {
    if (this.previewDebounce) clearTimeout(this.previewDebounce);
    if (!this.selectedWorkspace || !this.clockifyStartDate || !this.clockifyEndDate) return;
    this.clockifyPreviewData    = null;
    this.clockifyPreviewLoading = true;
    this.previewDebounce = setTimeout(() => this.loadClockifyPreview(), 800);
  }

  private loadClockifyPreview(): void {
    if (!this.selectedWorkspace || !this.clockifyStartDate || !this.clockifyEndDate) {
      this.clockifyPreviewLoading = false;
      return;
    }

    const payload = {
      workspace_id: this.selectedWorkspace,
      start_date:   this.formatDateLocal(this.clockifyStartDate, false),
      end_date:     this.formatDateLocal(this.clockifyEndDate, true),
      project_ids:  this.selectedClockifyProjects
    };

    this.http.post<any>(`${environment.apiUrl}/clockify/preview`, payload).subscribe({
      next: (data) => {
        this.clockifyPreviewData    = data;
        this.clockifyPreviewLoading = false;
        // Sütunları mevcut data'ya göre ayarla
        if (data.columns) {
          this.clockifyPreviewColumns = CLOCK_VISIBLE_COLS.filter(c => data.columns.includes(c));
        }
      },
      error: (err) => {
        this.clockifyPreviewLoading = false;
        // Sessizce başarısız ol — preview opsiyonel
        console.warn('Clockify preview failed:', err.error?.error);
      }
    });
  }

  private formatDateLocal(date: Date, isEnd: boolean): string {
    const pad = (n: number) => n.toString().padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}${isEnd ? 'T23:59:59.999Z' : 'T00:00:00.000Z'}`;
  }

  generateClockifyReport(): void {
    if (!this.clockifyStartDate || !this.clockifyEndDate) return;
    this.converting = true;
    const data = {
      workspace_id: this.selectedWorkspace,
      start_date:   this.formatDateLocal(this.clockifyStartDate, false),
      end_date:     this.formatDateLocal(this.clockifyEndDate, true),
      project_ids:  this.selectedClockifyProjects,
      format:       this.format
    };
    this.clockifyService.getTimeEntries(data).subscribe({
      next: (blob) => {
        saveAs(blob, `Clockify_Report_${Date.now()}.xlsx`);
        this.snackBar.open('Report generated!', 'Close', { duration: 3000 });
        this.converting = false;
      },
      error: (err) => {
        this.snackBar.open(err.error?.error || 'Error generating report', 'Close', { duration: 5000 });
        this.converting = false;
      }
    });
  }

  getUserDisplayName(): string {
    const user = this.authService.getCurrentUser();
    if (!user) return 'Guest';
    const profile = user.profile as any;
    return user.user_type === 'company' ? profile.company_name || user.email : profile.full_name || user.email;
  }
}