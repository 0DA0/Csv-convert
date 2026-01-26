import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface InvoiceService {
  description: string;
  hsn: string;
  quantity: number;
  rate: number;
  per: string;
}

export interface InvoiceData {
  invoice_no: string;
  invoice_date: string;
  delivery_note?: string;
  payment_terms?: string;
  ref_date?: string;
  other_references?: string;
  buyer_order_no?: string;
  order_date?: string;
  dispatch_doc_no?: string;
  delivery_note_date?: string;
  dispatched_through?: string;
  destination?: string;
  country?: string;
  lut_bond_no?: string;
  from?: string;
  to?: string;
  terms_of_delivery?: string;
  buyer_name: string;
  buyer_address?: string;
  buyer_state?: string;
  place_of_supply?: string;
  contact_person?: string;
  buyer_email?: string;
  services: InvoiceService[];
  bank_holder?: string;
  bank_name?: string;
  bank_account?: string;
  bank_branch?: string;
  bank_swift?: string;
}

@Injectable({
  providedIn: 'root'
})
export class InvoiceService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  generateInvoice(data: InvoiceData): Observable<Blob> {
    return this.http.post(`${this.apiUrl}/invoice/generate`, data, {
      responseType: 'blob'
    });
  }
}