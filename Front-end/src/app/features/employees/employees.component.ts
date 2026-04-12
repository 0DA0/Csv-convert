import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { MatSnackBar } from '@angular/material/snack-bar';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-employees',
  templateUrl: './employees.component.html',
  styleUrls: ['./employees.component.scss']
})
export class EmployeesComponent implements OnInit {
  employees: any[] = [];
  companyCode = '';
  loading = true;
  savingEmployee = false;
  searchQuery = '';

  displayedColumns = ['full_name', 'clockify_username', 'phone', 'status', 'created_at', 'actions'];

  editingEmployee: any = null;
  editForm: any = {};
  deletingEmployee: any = null;

  constructor(
    private http: HttpClient,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.loadEmployees();
    this.loadCompanyCode();
  }

  loadEmployees(): void {
    this.loading = true;
    this.http.get<any[]>(`${environment.apiUrl}/company/employees`).subscribe({
      next: (data) => { this.employees = data; this.loading = false; },
      error: () => { this.snackBar.open('Failed to load employees', 'Close', { duration: 3000 }); this.loading = false; }
    });
  }

  loadCompanyCode(): void {
    this.http.get<any>(`${environment.apiUrl}/company/code`).subscribe({
      next: (data) => { this.companyCode = data.company_code; },
      error: () => {}
    });
  }

  get filteredEmployees(): any[] {
    if (!this.searchQuery.trim()) return this.employees;
    const q = this.searchQuery.toLowerCase();
    return this.employees.filter(e =>
      (e.full_name || '').toLowerCase().includes(q) ||
      (e.email || '').toLowerCase().includes(q) ||
      (e.clockify_username || '').toLowerCase().includes(q)
    );
  }

  getInitials(name: string): string {
    if (!name) return '?';
    return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  }

  formatDate(dateStr: string): string {
    if (!dateStr) return '-';
    try { return new Date(dateStr).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }); }
    catch { return '-'; }
  }

  copyCode(): void {
    if (this.companyCode) {
      navigator.clipboard.writeText(this.companyCode);
      this.snackBar.open('Company code copied!', 'Close', { duration: 2000 });
    }
  }

  openEditDialog(emp: any): void {
    this.editingEmployee = emp;
    this.editForm = {
      full_name: emp.full_name || '',
      phone: emp.phone || '',
      clockify_username: emp.clockify_username || ''
    };
  }

  closeEditDialog(): void {
    this.editingEmployee = null;
    this.editForm = {};
  }

  saveEmployee(): void {
    if (!this.editingEmployee) return;
    this.savingEmployee = true;

    this.http.put(`${environment.apiUrl}/company/employees/${this.editingEmployee.id}`, this.editForm)
      .subscribe({
        next: () => {
          // Update local list
          const idx = this.employees.findIndex(e => e.id === this.editingEmployee.id);
          if (idx !== -1) {
            this.employees[idx] = { ...this.employees[idx], ...this.editForm };
          }
          this.snackBar.open('Employee updated', 'Close', { duration: 3000 });
          this.closeEditDialog();
          this.savingEmployee = false;
        },
        error: (err) => {
          this.snackBar.open(err.error?.error || 'Update failed', 'Close', { duration: 3000 });
          this.savingEmployee = false;
        }
      });
  }

  toggleStatus(emp: any): void {
    const newStatus = emp.status === 'active' ? 'inactive' : 'active';
    this.http.put(`${environment.apiUrl}/company/employees/${emp.id}`, { status: newStatus }).subscribe({
      next: () => {
        emp.status = newStatus;
        this.snackBar.open(`Employee ${newStatus === 'active' ? 'activated' : 'deactivated'}`, 'Close', { duration: 2000 });
      },
      error: (err) => { this.snackBar.open(err.error?.error || 'Update failed', 'Close', { duration: 3000 }); }
    });
  }

  confirmDelete(emp: any): void {
    this.deletingEmployee = emp;
  }

  cancelDelete(): void {
    this.deletingEmployee = null;
  }

  deleteEmployee(): void {
    if (!this.deletingEmployee) return;
    this.savingEmployee = true;

    this.http.delete(`${environment.apiUrl}/company/employees/${this.deletingEmployee.id}`)
      .subscribe({
        next: () => {
          this.employees = this.employees.filter(e => e.id !== this.deletingEmployee.id);
          this.snackBar.open('Employee removed', 'Close', { duration: 3000 });
          this.cancelDelete();
          this.savingEmployee = false;
        },
        error: (err) => {
          this.snackBar.open(err.error?.error || 'Delete failed', 'Close', { duration: 3000 });
          this.savingEmployee = false;
        }
      });
  }
}