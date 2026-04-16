import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../../core/services/auth.service';
import { ClockifyService } from '../../core/services/clockify.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { saveAs } from 'file-saver';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-employee-dashboard',
  templateUrl: './employee-dashboard.component.html',
  styleUrls: ['./employee-dashboard.component.scss']
})
export class EmployeeDashboardComponent implements OnInit {
  employeeName    = '';
  companyName     = '';
  clockifyUsername = '';

  workspaces: any[]        = [];
  projects: any[]          = [];
  selectedWorkspace        = '';
  selectedProjects: string[] = [];
  startDate: Date | null   = null;
  endDate:   Date | null   = null;
  format = 'hours';

  loading    = false;
  generating = false;
  connectionError = '';

  constructor(
    private authService: AuthService,
    private clockifyService: ClockifyService,
    private http: HttpClient,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    const user = this.authService.getCurrentUser();
    if (user) {
      const p = user.profile as any;
      this.employeeName     = p?.full_name        || user.email;
      this.companyName      = p?.company_name      || '';
      this.clockifyUsername = p?.clockify_username || '';
    }

    // Default: current month
    const now = new Date();
    this.startDate = new Date(now.getFullYear(), now.getMonth(), 1);
    this.endDate   = new Date(now.getFullYear(), now.getMonth() + 1, 0);

    this.loadWorkspaces();
  }

  loadWorkspaces(): void {
    this.loading = true;
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
        this.loading = false;
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

  // ── DÜZELTİLMİŞ: timezone-safe tarih formatlama ──
  private formatDateLocal(date: Date, isEnd: boolean): string {
    const pad = (n: number) => n.toString().padStart(2, '0');
    const y   = date.getFullYear();
    const mo  = pad(date.getMonth() + 1);
    const d   = pad(date.getDate());
    const time = isEnd ? 'T23:59:59.999Z' : 'T00:00:00.000Z';
    return `${y}-${mo}-${d}${time}`;
  }

  generateReport(): void {
    if (!this.startDate || !this.endDate) {
      this.snackBar.open('Please select start and end dates', 'Close', { duration: 3000 });
      return;
    }

    this.generating = true;

    // ── DÜZELTİLMİŞ: toISOString() yerine lokal bileşenlerden string üret ──
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
}