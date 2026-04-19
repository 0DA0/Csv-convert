import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup } from '@angular/forms';
import { AuthService } from '../../core/services/auth.service';
import { ClockifyService } from '../../core/services/clockify.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { User } from '../../core/models/user.model';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-profile',
  templateUrl: './profile.component.html',
  styleUrls: ['./profile.component.scss']
})
export class ProfileComponent implements OnInit {
  profileForm: FormGroup;
  loading = false;
  loadingProfile = true;
  hideApiKey = true;
  logoPreview: string | null = null;
  user: User | null = null;
  selectedDataSource: 'csv' | 'clockify' = 'csv';
  hasExistingApiKey = false;
  maskedApiKey = '';
  private apiKeyChecked = false;

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private clockifyService: ClockifyService,
    private http: HttpClient,
    private snackBar: MatSnackBar
  ) {
    this.profileForm = this.fb.group({
      full_name:        [''],
      company_name:     [''],
      contact_person:   [''],
      phone:            [''],
      address:          [''],
      logo_base64:      [''],
      logo_mimetype:    [''],
      data_source:      ['csv'],
      clockify_api_key: ['']
    });
  }

  ngOnInit(): void {
    const existing = this.authService.getCurrentUser();
    if (existing) {
      this.initFromUser(existing);
    } else {
      const sub = this.authService.currentUser$.subscribe(user => {
        if (user) {
          this.initFromUser(user);
          sub.unsubscribe();
        } else {
          setTimeout(() => { if (!this.user) this.loadingProfile = false; }, 2000);
        }
      });
    }
  }

  private initFromUser(user: User): void {
    this.loadingProfile = false;
    this.user = user;
    this.selectedDataSource = user.data_source || 'csv';

    const profile = user.profile as any;
    this.profileForm.patchValue({ data_source: user.data_source || 'csv' });

    if (user.user_type === 'individual' && 'full_name' in profile) {
      this.profileForm.patchValue({ full_name: profile.full_name, phone: profile.phone || '' });
    } else if (user.user_type === 'company' && 'company_name' in profile) {
      this.profileForm.patchValue({
        company_name:   profile.company_name,
        contact_person: profile.contact_person || '',
        phone:          profile.phone || '',
        address:        profile.address || ''
      });
      if (profile.logo_base64) this.logoPreview = profile.logo_base64;
    }

    if (user.data_source === 'clockify' && !this.apiKeyChecked) {
      this.checkExistingApiKey();
    }
  }

  checkExistingApiKey(): void {
    if (this.apiKeyChecked) return;
    this.apiKeyChecked = true;
    this.clockifyService.getApiKey().subscribe({
      next: (r) => { this.hasExistingApiKey = r.has_key; this.maskedApiKey = r.api_key || ''; },
      error: () => { this.hasExistingApiKey = false; }
    });
  }

  selectDataSource(source: 'csv' | 'clockify'): void {
    this.selectedDataSource = source;
    this.profileForm.patchValue({ data_source: source });
    if (source === 'clockify' && !this.apiKeyChecked) this.checkExistingApiKey();
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

    // 1) Profili kaydet
    this.http.put(`${environment.apiUrl}/profile`, formData).subscribe({
      next: () => {
        this.profileForm.patchValue({ clockify_api_key: '' });
        this.loading = false;
        this.snackBar.open('Profile updated successfully!', 'Close', { duration: 3000 });

        // 2) Güncel user'ı çek ve BehaviorSubject'i güncelle
        // Bu sayede dashboard'daki currentUser$ subscription hemen tetiklenir
        this.http.get<User>(`${environment.apiUrl}/auth/me`).subscribe({
          next: (freshUser) => {
            // AuthService private field'ına erişim — cast gerekiyor
            (this.authService as any).currentUserSubject.next(freshUser);

            // API key kontrolünü sıfırla (yeni data_source ile tekrar kontrol edilsin)
            if (formData.clockify_api_key) {
              this.apiKeyChecked = false;
              this.checkExistingApiKey();
            }
          },
          error: () => {}
        });
      },
      error: (err) => {
        this.snackBar.open(err.error?.error || 'Update failed', 'Close', { duration: 5000 });
        this.loading = false;
      }
    });
  }
}