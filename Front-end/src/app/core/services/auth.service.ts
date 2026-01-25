import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable, tap, catchError, of } from 'rxjs';
import { JwtHelperService } from '@auth0/angular-jwt';
import { environment } from '../../../environments/environment';
import { User, AuthResponse } from '../models/user.model';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = environment.apiUrl;
  private currentUserSubject = new BehaviorSubject<User | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();
  private jwtHelper = new JwtHelperService();
  private isLoadingUser = false;

  constructor(private http: HttpClient, private router: Router) {
    this.loadCurrentUser();
  }

  register(userData: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/auth/register`, userData);
  }

  login(email: string, password: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.apiUrl}/auth/login`, { email, password }).pipe(
      tap(response => {
        localStorage.setItem('access_token', response.access_token);
        this.currentUserSubject.next(response.user);
      })
    );
  }

  logout(): void {
    localStorage.removeItem('access_token');
    this.currentUserSubject.next(null);
    this.router.navigate(['/login']);
  }

  getToken(): string | null {
    return localStorage.getItem('access_token');
  }

  isAuthenticated(): boolean {
    const token = this.getToken();
    return token !== null && !this.jwtHelper.isTokenExpired(token);
  }

  getCurrentUser(): User | null {
    return this.currentUserSubject.value;
  }

  private loadCurrentUser(): void {
    if (this.isLoadingUser) return;
    
    const token = this.getToken();
    
    if (!token || this.jwtHelper.isTokenExpired(token)) {
      this.currentUserSubject.next(null);
      return;
    }

    this.isLoadingUser = true;
    
    this.http.get<User>(`${this.apiUrl}/auth/me`).pipe(
      catchError(error => {
        console.error('Error loading user:', error);
        if (error.status === 401) {
          this.logout();
        }
        this.isLoadingUser = false;
        return of(null);
      })
    ).subscribe({
      next: (user) => {
        if (user) {
          this.currentUserSubject.next(user);
        }
        this.isLoadingUser = false;
      }
    });
  }

  updateProfile(profileData: any): Observable<any> {
    return this.http.put(`${this.apiUrl}/profile`, profileData).pipe(
      tap(() => this.loadCurrentUser())
    );
  }
}