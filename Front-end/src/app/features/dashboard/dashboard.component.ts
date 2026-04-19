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

  // Data source — reacts to profile changes
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
  clockifyWorkspaces:       any[] = [];
  clockifyProjects:         any[] = [];
  selectedWorkspace         = '';
  selectedClockifyProjects: string[] = [];
  clockifyStartDate: Date | null = null;
  clockifyEndDate:   Date | null = null;
  clockifyLoading = false;
  private workspacesLoaded = false;

  private userSub?: Subscription;

  constructor(
    public authService: AuthService,
    private csvService: CsvService,
    private clockifyService: ClockifyService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.setDefaultDates();

    // Subscribe for the full lifetime of the component so profile changes
    // (CSV ↔ Clockify switch) are immediately reflected on the dashboard.
    this.userSub = this.authService.currentUser$.subscribe(user => {
      if (!user) return;

      const newSource = user.data_source || 'csv';

      // Reset Clockify state when switching away from Clockify
      if (this.userDataSource === 'clockify' && newSource === 'csv') {
        this.clockifyWorkspaces = [];
        this.workspacesLoaded   = false;
      }

      this.userDataSource = newSource;

      // Auto-connect Clockify on first load or after switching to it
      if (newSource === 'clockify' && !this.workspacesLoaded && !this.clockifyLoading) {
        this.loadClockifyWorkspaces();
      }
    });
  }

  ngOnDestroy(): void {
    this.userSub?.unsubscribe();
  }

  // ── Helpers ────────────────────────────────────────

  setDefaultDates(): void {
    const now = new Date();
    this.clockifyStartDate = new Date(now.getFullYear(), now.getMonth(), 1);
    this.clockifyEndDate   = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  }

  getUserDisplayName(): string {
    const user = this.authService.getCurrentUser();
    if (!user) return 'Guest';
    const p = user.profile as any;
    return user.user_type === 'company' ? p.company_name || user.email : p.full_name || user.email;
  }

  private formatDateLocal(date: Date, isEnd: boolean): string {
    const pad = (n: number) => n.toString().padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}${
      isEnd ? 'T23:59:59.999Z' : 'T00:00:00.000Z'
    }`;
  }

  // ── CSV ────────────────────────────────────────────

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
    this.selectedProjects = [];
    this.selectedClients  = [];
    this.selectedUsers    = [];
  }

  // ── Clockify ───────────────────────────────────────

  loadClockifyWorkspaces(): void {
    if (this.workspacesLoaded || this.clockifyLoading) return;
    this.clockifyLoading = true;
    this.clockifyService.getWorkspaces('').subscribe({
      next: (ws) => {
        this.clockifyWorkspaces = ws;
        this.clockifyLoading    = false;
        this.workspacesLoaded   = true;
      },
      error: () => {
        this.clockifyLoading = false;
        this.snackBar.open(
          'Failed to connect to Clockify. Please check your API key in profile.',
          'Close', { duration: 5000 }
        );
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
}