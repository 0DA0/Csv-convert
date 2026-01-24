import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { AuthService } from '../../core/services/auth.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { User } from '../../core/models/user.model';

@Component({
  selector: 'app-profile',
  templateUrl: './profile.component.html',
  styleUrls: ['./profile.component.scss']
})
export class ProfileComponent implements OnInit {
  profileForm: FormGroup;
  loading = false;
  hideApiKey = true;
  logoPreview: string | null = null;
  user: User | null = null;
  selectedDataSource: 'csv' | 'clockify' = 'csv';

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private snackBar: MatSnackBar
  ) {
    this.profileForm = this.fb.group({
      full_name: [''],
      company_name: [''],
      contact_person: [''],
      phone: [''],
      address: [''],
      logo_base64: [''],
      logo_mimetype: [''],
      data_source: ['csv'],
      clockify_api_key: ['']
    });
  }

  ngOnInit(): void {
    this.authService.currentUser$.subscribe(user => {
      if (user) {
        this.user = user;
        this.selectedDataSource = user.data_source || 'csv';
        
        const profile = user.profile;
        
        this.profileForm.patchValue({
          data_source: user.data_source || 'csv'
        });
        
        if (user.user_type === 'individual' && 'full_name' in profile) {
          this.profileForm.patchValue({
            full_name: profile.full_name,
            phone: profile.phone || ''
          });
        } else if (user.user_type === 'company' && 'company_name' in profile) {
          this.profileForm.patchValue({
            company_name: profile.company_name,
            contact_person: profile.contact_person || '',
            phone: profile.phone || '',
            address: profile.address || ''
          });
          
          if (profile.logo_base64) {
            this.logoPreview = profile.logo_base64;
          }
        }
      }
    });
  }

  selectDataSource(source: 'csv' | 'clockify'): void {
    this.selectedDataSource = source;
    this.profileForm.patchValue({ data_source: source });
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
        this.profileForm.patchValue({
          logo_base64: e.target.result,
          logo_mimetype: file.type
        });
      };
      reader.readAsDataURL(file);
    }
  }

  onSubmit(): void {
    if (this.profileForm.invalid) return;

    this.loading = true;
    const formData = this.profileForm.value;

    this.authService.updateProfile(formData).subscribe({
      next: () => {
        this.snackBar.open('Profile updated successfully!', 'Close', { duration: 3000 });
        this.loading = false;
        
        // API key temizle (güvenlik için)
        this.profileForm.patchValue({ clockify_api_key: '' });
      },
      error: (error) => {
        this.snackBar.open(error.error?.error || 'Update failed', 'Close', { duration: 5000 });
        this.loading = false;
      }
    });
  }
}