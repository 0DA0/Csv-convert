import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, AbstractControl, ValidationErrors } from '@angular/forms';
import { AuthService } from '../../core/services/auth.service';
import { ClockifyService } from '../../core/services/clockify.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { User } from '../../core/models/user.model';

function passwordMatchValidator(group: AbstractControl): ValidationErrors | null {
  const np = group.get('new_password')?.value;
  const cp = group.get('confirm_password')?.value;
  return np === cp ? null : { mismatch: true };
}

@Component({
  selector: 'app-profile',
  templateUrl: './profile.component.html',
  styleUrls: ['./profile.component.scss']
})
export class ProfileComponent implements OnInit {
  profileForm:  FormGroup;
  passwordForm: FormGroup;

  loading          = false;
  loadingProfile   = true;
  changingPassword = false;

  hideApiKey    = true;
  hideCurrentPw = true;
  hideNewPw     = true;
  hideConfirmPw = true;

  logoPreview: string | null = null;
  user: User | null = null;
  selectedDataSource: 'csv' | 'clockify' = 'csv';
  hasExistingApiKey = false;

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private clockifyService: ClockifyService,
    private snackBar: MatSnackBar
  ) {
    this.profileForm = this.fb.group({
      full_name: [''], company_name: [''], contact_person: [''],
      phone: [''], address: [''], logo_base64: [''], logo_mimetype: [''],
      data_source: ['csv'], clockify_api_key: ['']
    });

    this.passwordForm = this.fb.group({
      current_password: ['', Validators.required],
      new_password:     ['', [Validators.required, Validators.minLength(8)]],
      confirm_password: ['', Validators.required]
    }, { validators: passwordMatchValidator });
  }

  ngOnInit(): void {
    this.authService.currentUser$.subscribe(user => {
      if (user) {
        this.loadingProfile = false;
        this.user = user;
        this.selectedDataSource = user.data_source || 'csv';
        const profile = user.profile as any;

        this.profileForm.patchValue({ data_source: user.data_source || 'csv' });

        if (user.data_source === 'clockify') this.checkExistingApiKey();

        if (user.user_type === 'individual' && 'full_name' in profile) {
          this.profileForm.patchValue({ full_name: profile.full_name, phone: profile.phone || '' });
        } else if (user.user_type === 'company' && 'company_name' in profile) {
          this.profileForm.patchValue({
            company_name:    profile.company_name,
            contact_person:  profile.contact_person || '',
            phone:           profile.phone || '',
            address:         profile.address || ''
          });
          if (profile.logo_base64) this.logoPreview = profile.logo_base64;
        }
      } else {
        setTimeout(() => {
          if (!this.authService.getCurrentUser()) this.loadingProfile = false;
        }, 2000);
      }
    });
  }

  checkExistingApiKey(): void {
    this.clockifyService.getApiKey().subscribe({
      next: (res) => { this.hasExistingApiKey = res.has_key; },
      error: () => { this.hasExistingApiKey = false; }
    });
  }

  selectDataSource(source: 'csv' | 'clockify'): void {
    this.selectedDataSource = source;
    this.profileForm.patchValue({ data_source: source });
    if (source === 'clockify') this.checkExistingApiKey();
  }

  onFileSelected(event: any): void {
    const file: File = event.target.files[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      this.snackBar.open('File size must be less than 2MB', 'Close', { duration: 3000 }); return;
    }
    const reader = new FileReader();
    reader.onload = (e: any) => {
      this.logoPreview = e.target.result;
      this.profileForm.patchValue({ logo_base64: e.target.result, logo_mimetype: file.type });
    };
    reader.readAsDataURL(file);
  }

  onSubmit(): void {
    if (this.profileForm.invalid) return;
    this.loading = true;
    const formData = { ...this.profileForm.value };

    if (this.hasExistingApiKey && (!formData.clockify_api_key || !formData.clockify_api_key.trim())) {
      delete formData.clockify_api_key;
    }

    this.authService.updateProfile(formData).subscribe({
      next: () => {
        this.snackBar.open('Profile updated successfully!', 'Close', { duration: 3000 });
        this.loading = false;
        this.profileForm.patchValue({ clockify_api_key: '' });
        if (this.selectedDataSource === 'clockify') {
          setTimeout(() => this.checkExistingApiKey(), 500);
        }
      },
      error: (error) => {
        this.snackBar.open(error.error?.error || 'Update failed', 'Close', { duration: 5000 });
        this.loading = false;
      }
    });
  }

  onChangePassword(): void {
    if (this.passwordForm.invalid) return;
    this.changingPassword = true;

    const { current_password, new_password } = this.passwordForm.value;

    this.authService.changePassword(current_password, new_password).subscribe({
      next: () => {
        this.snackBar.open('Password changed successfully!', 'Close', { duration: 3000 });
        this.passwordForm.reset();
        this.changingPassword = false;
      },
      error: (err) => {
        this.snackBar.open(err.error?.error || 'Password change failed', 'Close', { duration: 5000 });
        this.changingPassword = false;
      }
    });
  }
}