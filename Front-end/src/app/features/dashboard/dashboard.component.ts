import { Component } from '@angular/core';
import { AuthService } from '../../core/services/auth.service';
import { CsvService } from '../../core/services/csv.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { saveAs } from 'file-saver';

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss']
})
export class DashboardComponent {
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

  constructor(
    public authService: AuthService,
    private csvService: CsvService,
    private snackBar: MatSnackBar
  ) {}

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
      error: (error) => {
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