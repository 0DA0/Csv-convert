import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, FormArray, Validators } from '@angular/forms';
import { InvoiceService as InvoiceAPIService, InvoiceData } from '../../core/services/invoice.service';
import { AuthService } from '../../core/services/auth.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { saveAs } from 'file-saver';

@Component({
  selector: 'app-invoice',
  templateUrl: './invoice.component.html',
  styleUrls: ['./invoice.component.scss']
})
export class InvoiceComponent implements OnInit {
  invoiceForm: FormGroup;
  loading = false;
  logoPreview: string | null = null;
  userType: 'individual' | 'company' = 'individual';
  
  // Seller bilgileri (preview için)
  sellerName = '';
  sellerAddress = '';
  sellerPhone = '';
  sellerEmail = '';

  constructor(
    private fb: FormBuilder,
    private invoiceService: InvoiceAPIService,
    private authService: AuthService,
    private snackBar: MatSnackBar
  ) {
    this.invoiceForm = this.createForm();
  }

  ngOnInit(): void {
    this.loadUserDefaults();
    this.addService(); // İlk servis satırını ekle
    
    // Form değişikliklerini dinle (preview için)
    this.invoiceForm.valueChanges.subscribe(() => {
      this.updateSellerInfo();
    });
  }

  createForm(): FormGroup {
    return this.fb.group({
      // Seller Information (Bireysel için)
      seller_name: [''],
      seller_address: [''],
      seller_phone: [''],
      seller_email: [''],
      
      // Invoice Details
      invoice_no: ['', Validators.required],
      invoice_date: [this.formatDate(new Date()), Validators.required],
      delivery_note: [''],
      payment_terms: ['Online'],
      ref_date: [''],
      other_references: ['--'],
      buyer_order_no: [''],
      order_date: [this.formatDate(new Date())],
      dispatch_doc_no: [''],
      delivery_note_date: [''],
      dispatched_through: [''],
      destination: [''],
      country: [''],
      lut_bond_no: [''],
      from: [''],
      to: [''],
      terms_of_delivery: [''],
      
      // Buyer Information
      buyer_name: ['', Validators.required],
      buyer_address: [''],
      buyer_state: [''],
      place_of_supply: [''],
      contact_person: [''],
      buyer_email: ['', Validators.email],
      
      // Services
      services: this.fb.array([]),
      
      // Bank Details
      bank_holder: [''],
      bank_name: [''],
      bank_account: [''],
      bank_branch: [''],
      bank_swift: ['']
    });
  }

  get services(): FormArray {
    return this.invoiceForm.get('services') as FormArray;
  }

  createServiceGroup(): FormGroup {
    return this.fb.group({
      description: ['', Validators.required],
      hsn: [''],
      quantity: [1, [Validators.required, Validators.min(0)]],
      rate: [0, [Validators.required, Validators.min(0)]],
      per: ['Hour', Validators.required]
    });
  }

  addService(): void {
    this.services.push(this.createServiceGroup());
  }

  removeService(index: number): void {
    if (this.services.length > 1) {
      this.services.removeAt(index);
    } else {
      this.snackBar.open('At least one service is required', 'Close', { duration: 3000 });
    }
  }

  calculateServiceAmount(index: number): number {
    const service = this.services.at(index).value;
    return (service.quantity || 0) * (service.rate || 0);
  }

  calculateTotalQuantity(): number {
    return this.services.controls.reduce((sum, control) => {
      return sum + (control.get('quantity')?.value || 0);
    }, 0);
  }

  calculateTotalAmount(): number {
    return this.services.controls.reduce((sum, control, index) => {
      return sum + this.calculateServiceAmount(index);
    }, 0);
  }

  numberToWords(num: number): string {
    if (num === 0) return 'Zero';
    
    const units = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine'];
    const teens = ['Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen'];
    const tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety'];
    const thousands = ['', 'Thousand', 'Million', 'Billion'];

    let words = '';
    let thousandIndex = 0;
    let n = Math.floor(num);

    while (n > 0) {
      let part = n % 1000;
      if (part > 0) {
        let partWords = '';
        if (part >= 100) {
          partWords += units[Math.floor(part / 100)] + ' Hundred ';
          part %= 100;
        }
        if (part >= 20) {
          partWords += tens[Math.floor(part / 10)] + ' ';
          part %= 10;
        }
        if (part >= 10) {
          partWords += teens[part - 10] + ' ';
          part = 0;
        }
        if (part > 0) {
          partWords += units[part] + ' ';
        }
        words = partWords + thousands[thousandIndex] + ' ' + words;
      }
      n = Math.floor(n / 1000);
      thousandIndex++;
    }
    return words.trim();
  }

  loadUserDefaults(): void {
    const user = this.authService.getCurrentUser();
    if (!user) return;
    
    this.userType = user.user_type;
    
    if (user.user_type === 'company') {
      const profile = user.profile as any;
      
      // Şirket bilgilerini yükle
      this.sellerName = profile.company_name || '';
      this.sellerAddress = profile.address || '';
      this.sellerPhone = profile.phone || '';
      this.sellerEmail = user.email || '';
      
      // Logo varsa göster
      if (profile.logo_base64) {
        this.logoPreview = profile.logo_base64;
      }
    } else {
      // Bireysel kullanıcı
      const profile = user.profile as any;
      
      this.sellerName = profile.full_name || '';
      this.sellerPhone = profile.phone || '';
      this.sellerEmail = user.email || '';
      
      // Form'u doldur
      this.invoiceForm.patchValue({
        seller_name: this.sellerName,
        seller_phone: this.sellerPhone,
        seller_email: this.sellerEmail
      });
    }
  }

  updateSellerInfo(): void {
    if (this.userType === 'individual') {
      this.sellerName = this.invoiceForm.get('seller_name')?.value || '';
      this.sellerAddress = this.invoiceForm.get('seller_address')?.value || '';
      this.sellerPhone = this.invoiceForm.get('seller_phone')?.value || '';
      this.sellerEmail = this.invoiceForm.get('seller_email')?.value || '';
    }
  }

  formatDate(date: Date): string {
    return date.toISOString().split('T')[0];
  }

  onSubmit(): void {
    if (this.invoiceForm.invalid) {
      this.snackBar.open('Please fill all required fields', 'Close', { duration: 3000 });
      return;
    }

    this.loading = true;
    const formData: any = { ...this.invoiceForm.value };
    
    // Bireysel kullanıcı için seller bilgilerini ekle
    if (this.userType === 'individual') {
      formData.seller_address = this.invoiceForm.get('seller_address')?.value || '';
    }

    this.invoiceService.generateInvoice(formData).subscribe({
      next: (blob) => {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
        const filename = `Invoice_${formData.invoice_no || timestamp}.xlsx`;
        saveAs(blob, filename);
        this.snackBar.open('Invoice generated successfully!', 'Close', { duration: 3000 });
        this.loading = false;
      },
      error: (error) => {
        this.snackBar.open(error.error?.error || 'Error generating invoice', 'Close', { duration: 5000 });
        this.loading = false;
      }
    });
  }

  resetForm(): void {
    this.invoiceForm.reset({
      invoice_date: this.formatDate(new Date()),
      order_date: this.formatDate(new Date()),
      payment_terms: 'Online',
      other_references: '--',
      seller_name: this.sellerName,
      seller_phone: this.sellerPhone,
      seller_email: this.sellerEmail
    });
    
    // Tüm servisleri temizle ve bir tane ekle
    while (this.services.length > 0) {
      this.services.removeAt(0);
    }
    this.addService();
  }
}