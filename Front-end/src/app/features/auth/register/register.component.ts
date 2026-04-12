import { Component } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { MatSnackBar } from '@angular/material/snack-bar';

@Component({
  selector: 'app-register',
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.scss']
})
export class RegisterComponent {
  registerForm: FormGroup;
  loading = false;
  hidePassword = true;
  hideApiKey = true;
  selectedUserType: 'individual' | 'company' | 'employee' = 'individual';
  selectedDataSource: 'csv' | 'clockify' = 'csv';
  logoPreview: string | null = null;
  registeredCompanyCode: string | null = null;

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router,
    private snackBar: MatSnackBar
  ) {
    this.registerForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(8)]],
      user_type: ['individual'],
      data_source: ['csv'],
      // individual / company shared
      full_name: [''],
      phone: [''],
      // company only
      company_name: [''],
      contact_person: [''],
      address: [''],
      logo_base64: [''],
      logo_mimetype: [''],
      // employee only
      company_code: [''],
      clockify_username: [''],
      // clockify
      clockify_api_key: ['']
    });

    this.updateValidators();
  }

  selectUserType(type: 'individual' | 'company' | 'employee'): void {
    this.selectedUserType = type;
    this.registerForm.patchValue({ user_type: type });
    this.updateValidators();
  }

  selectDataSource(source: 'csv' | 'clockify'): void {
    this.selectedDataSource = source;
    this.registerForm.patchValue({ data_source: source });
    this.updateValidators();
  }

  private updateValidators(): void {
    const fullName       = this.registerForm.get('full_name');
    const companyName    = this.registerForm.get('company_name');
    const companyCode    = this.registerForm.get('company_code');
    const clockifyApiKey = this.registerForm.get('clockify_api_key');

    fullName?.clearValidators();
    companyName?.clearValidators();
    companyCode?.clearValidators();
    clockifyApiKey?.clearValidators();

    if (this.selectedUserType === 'individual') {
      fullName?.setValidators([Validators.required]);
    } else if (this.selectedUserType === 'company') {
      companyName?.setValidators([Validators.required]);
      if (this.selectedDataSource === 'clockify') {
        clockifyApiKey?.setValidators([Validators.required]);
      }
    } else if (this.selectedUserType === 'employee') {
      fullName?.setValidators([Validators.required]);
      companyCode?.setValidators([Validators.required, Validators.minLength(8), Validators.maxLength(8)]);
    }

    fullName?.updateValueAndValidity();
    companyName?.updateValueAndValidity();
    companyCode?.updateValueAndValidity();
    clockifyApiKey?.updateValueAndValidity();
  }

  onFileSelected(event: any): void {
    const file: File = event.target.files[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      this.snackBar.open('File size must be less than 2MB', 'Close', { duration: 3000 });
      return;
    }
    const reader = new FileReader();
    reader.onload = (e: any) => {
      this.logoPreview = e.target.result;
      this.registerForm.patchValue({ logo_base64: e.target.result, logo_mimetype: file.type });
    };
    reader.readAsDataURL(file);
  }

  removeLogo(): void {
    this.logoPreview = null;
    this.registerForm.patchValue({ logo_base64: '', logo_mimetype: '' });
  }

  copyCode(): void {
    if (this.registeredCompanyCode) {
      navigator.clipboard.writeText(this.registeredCompanyCode);
      this.snackBar.open('Company code copied!', 'Close', { duration: 2000 });
    }
  }

  onSubmit(): void {
    if (this.registerForm.invalid) return;
    this.loading = true;
    const formData = { ...this.registerForm.value };

    // company_code büyük harfe çevir
    if (formData.company_code) {
      formData.company_code = formData.company_code.toUpperCase();
    }

    this.authService.register(formData).subscribe({
      next: (res: any) => {
        this.loading = false;
        if (this.selectedUserType === 'company' && res.company_code) {
          this.registeredCompanyCode = res.company_code;
        } else {
          this.snackBar.open('Registration successful! Please login.', 'Close', { duration: 3000 });
          this.router.navigate(['/login']);
        }
      },
      error: (error: any) => {
        this.snackBar.open(error.error?.error || 'Registration failed', 'Close', { duration: 5000 });
        this.loading = false;
      }
    });
  }
}