import { Component, OnInit, AfterViewInit, ElementRef } from '@angular/core';
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
export class InvoiceComponent implements OnInit, AfterViewInit {
  invoiceForm: FormGroup;
  loading = false;
  logoPreview: string | null = null;
  companyName = '';
  companyAddress = '';
  companyPhone = '';
  companyEmail = '';

  constructor(
    private fb: FormBuilder,
    private invoiceService: InvoiceAPIService,
    private authService: AuthService,
    private snackBar: MatSnackBar,
    private elementRef: ElementRef
  ) {
    this.invoiceForm = this.createForm();
  }

  ngOnInit(): void {
    this.loadUserDefaults();
    // İlk service'i başlangıçta ekle
    this.addService();
    
    // Form değişikliklerini dinle - debug için
    this.invoiceForm.statusChanges.subscribe(status => {
      console.log('Form status:', status);
      if (status === 'INVALID') {
        this.logInvalidFields();
      }
    });
  }

  ngAfterViewInit(): void {
    this.syncPanelHeights();
    
    this.invoiceForm.valueChanges.subscribe(() => {
      setTimeout(() => this.syncPanelHeights(), 100);
    });
    
    window.addEventListener('resize', () => this.syncPanelHeights());
  }

  private syncPanelHeights(): void {
    const rightPanel = this.elementRef.nativeElement.querySelector('.right-panel');
    const leftPanel = this.elementRef.nativeElement.querySelector('.left-panel');
    
    if (rightPanel && leftPanel && window.innerWidth > 768) {
      const rightPanelHeight = rightPanel.offsetHeight;
      leftPanel.style.maxHeight = `${rightPanelHeight}px`;
    } else if (leftPanel) {
      leftPanel.style.maxHeight = 'none';
    }
  }

  createForm(): FormGroup {
    return this.fb.group({
      // Invoice Details - Sadece zorunlu alanlar required
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
      
      // Buyer Information - Sadece buyer_name required
      buyer_name: ['', Validators.required],
      buyer_address: [''],
      buyer_state: [''],
      place_of_supply: [''],
      contact_person: [''],
      buyer_email: [''], // Email validation kaldırıldı
      
      // Services - En az 1 service gerekli
      services: this.fb.array([], Validators.required),
      
      // Bank Details - Opsiyonel
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
      quantity: [1, [Validators.required, Validators.min(0.01)]],
      rate: [0, [Validators.required, Validators.min(0)]],
      per: ['Hour', Validators.required]
    });
  }

  addService(): void {
    this.services.push(this.createServiceGroup());
    setTimeout(() => this.syncPanelHeights(), 100);
  }

  removeService(index: number): void {
    if (this.services.length > 1) {
      this.services.removeAt(index);
      setTimeout(() => this.syncPanelHeights(), 100);
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
    if (user && user.user_type === 'company') {
      const profile = user.profile as any;
      
      if (profile.company_name) {
        this.companyName = profile.company_name;
      }
      if (profile.address) {
        this.companyAddress = profile.address;
      }
      if (profile.phone) {
        this.companyPhone = profile.phone;
      }
      if (profile.contact_person) {
        this.companyEmail = profile.contact_person;
      }
      
      if (profile.logo_base64) {
        this.logoPreview = profile.logo_base64;
      }
    }
  }

  formatDate(date: Date): string {
    return date.toISOString().split('T')[0];
  }

  // Hangi alanların invalid olduğunu göster
  logInvalidFields(): void {
    const invalidFields: string[] = [];
    
    Object.keys(this.invoiceForm.controls).forEach(key => {
      const control = this.invoiceForm.get(key);
      if (control && control.invalid) {
        if (key === 'services') {
          const servicesArray = control as FormArray;
          servicesArray.controls.forEach((serviceControl, index) => {
            Object.keys((serviceControl as FormGroup).controls).forEach(serviceKey => {
              const serviceField = serviceControl.get(serviceKey);
              if (serviceField && serviceField.invalid) {
                invalidFields.push(`Service ${index + 1} - ${serviceKey}`);
              }
            });
          });
        } else {
          invalidFields.push(key);
        }
      }
    });
    
    if (invalidFields.length > 0) {
      console.log('Invalid fields:', invalidFields);
    }
  }

  // Eksik alanları kullanıcıya göster
  showMissingFields(): void {
    const invalidFields: string[] = [];
    
    // Invoice details
    if (this.invoiceForm.get('invoice_no')?.invalid) {
      invalidFields.push('Invoice No');
    }
    if (this.invoiceForm.get('invoice_date')?.invalid) {
      invalidFields.push('Invoice Date');
    }
    
    // Buyer info
    if (this.invoiceForm.get('buyer_name')?.invalid) {
      invalidFields.push('Buyer Name');
    }
    
    // Services
    if (this.services.length === 0) {
      invalidFields.push('At least one service');
    } else {
      this.services.controls.forEach((service, index) => {
        const serviceGroup = service as FormGroup;
        if (serviceGroup.get('description')?.invalid) {
          invalidFields.push(`Service ${index + 1} - Description`);
        }
        if (serviceGroup.get('quantity')?.invalid) {
          invalidFields.push(`Service ${index + 1} - Quantity`);
        }
        if (serviceGroup.get('rate')?.invalid) {
          invalidFields.push(`Service ${index + 1} - Rate`);
        }
        if (serviceGroup.get('per')?.invalid) {
          invalidFields.push(`Service ${index + 1} - Unit`);
        }
      });
    }
    
    if (invalidFields.length > 0) {
      const message = `Please fill required fields:\n${invalidFields.join('\n')}`;
      this.snackBar.open(message, 'Close', { 
        duration: 5000,
        verticalPosition: 'top'
      });
    }
  }

  onSubmit(): void {
    if (this.invoiceForm.invalid) {
      this.showMissingFields();
      
      // Tüm alanları "touched" yap ki validation mesajları görünsün
      Object.keys(this.invoiceForm.controls).forEach(key => {
        const control = this.invoiceForm.get(key);
        control?.markAsTouched();
        
        if (key === 'services') {
          const servicesArray = control as FormArray;
          servicesArray.controls.forEach(serviceControl => {
            Object.keys((serviceControl as FormGroup).controls).forEach(serviceKey => {
              serviceControl.get(serviceKey)?.markAsTouched();
            });
          });
        }
      });
      
      return;
    }

    this.loading = true;
    const formData: InvoiceData = this.invoiceForm.value;

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

  // Form validation durumunu kontrol et
  isFormValid(): boolean {
    return this.invoiceForm.valid;
  }

  resetForm(): void {
    this.invoiceForm.reset({
      invoice_date: this.formatDate(new Date()),
      order_date: this.formatDate(new Date()),
      payment_terms: 'Online',
      other_references: '--'
    });
    
    while (this.services.length > 0) {
      this.services.removeAt(0);
    }
    this.addService();
    
    setTimeout(() => this.syncPanelHeights(), 100);
  }
}