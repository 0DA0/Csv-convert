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
  user: User | null = null;
  logoPreview: string | null = null;

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
      logo_mimetype: ['']
    });
  }

  ngOnInit(): void {
    this.authService.currentUser$.subscribe(user => {
      if (user) {
        this.user = user;
        if (user.user_type === 'individual') {
          this.profileForm.patchValue({
            full_name: user.profile.full_name,
            phone: user.profile.phone || ''
          });
        } else {
          this.profileForm.patchValue({
            company_name: user.profile.company_name,
            contact_person: user.profile.contact_person || '',
            phone: user.profile.phone || '',
            address: user.profile.address || ''
          });
          if (user.profile.logo_base64) {
            this.logoPreview = user.profile.logo_base64;
          }
        }
      }
    });
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
    this.authService.updateProfile(this.profileForm.value).subscribe({
      next: () => {
        this.snackBar.open('Profile updated successfully!', 'Close', { duration: 3000 });
        this.loading = false;
      },
      error: (error) => {
        this.snackBar.open('Error updating profile', 'Close', { duration: 3000 });
        this.loading = false;
      }
    });
  }
}