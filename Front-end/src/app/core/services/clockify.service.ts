import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ClockifyService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getWorkspaces(apiKey: string): Observable<any> {
    const headers = new HttpHeaders({ 'X-Clockify-Api-Key': apiKey });
    return this.http.get(`${this.apiUrl}/clockify/workspaces`, { headers });
  }

  getProjects(apiKey: string, workspaceId: string): Observable<any> {
    const headers = new HttpHeaders({ 'X-Clockify-Api-Key': apiKey });
    return this.http.get(`${this.apiUrl}/clockify/projects?workspace_id=${workspaceId}`, { headers });
  }

  getTimeEntries(data: any): Observable<Blob> {
    return this.http.post(`${this.apiUrl}/clockify/time-entries`, data, {
      responseType: 'blob'
    });
  }

  saveApiKey(apiKey: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/clockify/save-api-key`, { api_key: apiKey });
  }

  getApiKey(): Observable<any> {
    return this.http.get(`${this.apiUrl}/clockify/get-api-key`);
  }
}