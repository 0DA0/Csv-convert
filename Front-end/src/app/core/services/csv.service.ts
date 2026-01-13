import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class CsvService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  previewCsv(file: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post(`${this.apiUrl}/csv/preview`, formData);
  }

  convertToExcel(file: File, filters: any): Observable<Blob> {
    const formData = new FormData();
    formData.append('file', file);
    
    if (filters.projects) {
      filters.projects.forEach((p: string) => formData.append('projects[]', p));
    }
    if (filters.clients) {
      filters.clients.forEach((c: string) => formData.append('clients[]', c));
    }
    if (filters.users) {
      filters.users.forEach((u: string) => formData.append('users[]', u));
    }
    if (filters.format) {
      formData.append('format', filters.format);
    }

    return this.http.post(`${this.apiUrl}/csv/convert`, formData, {
      responseType: 'blob'
    });
  }
}