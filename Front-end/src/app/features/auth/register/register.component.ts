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
  selectedUserType: 'individual' | 'company' = 'individual';
  selectedDataSource: 'csv' | 'clockify' = 'csv';
  logoPreview: string | null = null;

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router,
    private snackBar: MatSnackBar
  ) {
    this.registerForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]],
      user_type: ['individual'],
      data_source: ['csv'],
      full_name: [''],
      company_name: [''],
      contact_person: [''],
      phone: [''],
      address: [''],
      logo_base64: [''],
      logo_mimetype: [''],
      clockify_api_key: ['']
    });

    this.updateValidators();
  }

  selectUserType(type: 'individual' | 'company'): void {
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
    const fullName = this.registerForm.get('full_name');
    const companyName = this.registerForm.get('company_name');
    const clockifyApiKey = this.registerForm.get('clockify_api_key');

    // User type validators
    if (this.selectedUserType === 'individual') {
      fullName?.setValidators([Validators.required]);
      companyName?.clearValidators();
    } else {
      fullName?.clearValidators();
      companyName?.setValidators([Validators.required]);
    }

    // Data source validators
    if (this.selectedDataSource === 'clockify') {
      clockifyApiKey?.setValidators([Validators.required]);
    } else {
      clockifyApiKey?.clearValidators();
    }

    fullName?.updateValueAndValidity();
    companyName?.updateValueAndValidity();
    clockifyApiKey?.updateValueAndValidity();
  }

  onFileSelected(event: any): void {
    const file: File = event.target.files[0];
    if (file) {
      if (file.size > 2 * 1024 * 1024) {
        this.snackBar.open('File size must be less than 2MB', 'Close', { duration: 3000 });
        return;
      }

      const reader = new FileReader();
      reader.onload = (e: any) => {
        this.logoPreview = e.target.result;
        this.registerForm.patchValue({
          logo_base64: e.target.result,
          logo_mimetype: file.type
        });
      };
      reader.readAsDataURL(file);
    }
  }

  removeLogo(): void {
    this.logoPreview = null;
    this.registerForm.patchValue({
      logo_base64: '',
      logo_mimetype: ''
    });
  }

  onSubmit(): void {
    if (this.registerForm.invalid) return;

    this.loading = true;
    const formData = this.registerForm.value;

    this.authService.register(formData).subscribe({
      next: () => {
        this.snackBar.open('Registration successful! Please login.', 'Close', { duration: 3000 });
        this.router.navigate(['/login']);
      },
      error: (error) => {
        this.snackBar.open(error.error?.error || 'Registration failed', 'Close', { duration: 5000 });
        this.loading = false;
      }
    });
  }
}