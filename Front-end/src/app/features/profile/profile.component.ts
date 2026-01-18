ngOnInit(): void {
  this.authService.getCurrentUser().subscribe(user => {
    if (user) {
      const profile = user.profile;
      
      // Type guard ile kontrol
      if (user.user_type === 'individual' && 'full_name' in profile) {
        this.profileForm.patchValue({
          full_name: profile.full_name,
          phone: user.phone || ''
        });
      } else if (user.user_type === 'company' && 'company_name' in profile) {
        this.profileForm.patchValue({
          company_name: profile.company_name,
          contact_person: profile.contact_person || '',
          contact_phone: profile.contact_phone || '',
          address: profile.address || ''
        });
        
        if (profile.logo_base64) {
          this.logoPreview = profile.logo_base64;
        }
      }
    }
  });
}