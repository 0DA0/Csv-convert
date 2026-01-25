import { Injectable } from '@angular/core';
import { Router, UrlTree } from '@angular/router';
import { Observable } from 'rxjs';
import { AuthService } from '../services/auth.service';

@Injectable({
  providedIn: 'root'
})
export class AuthGuard {
  constructor(private authService: AuthService, private router: Router) {}

  canActivate(): boolean | UrlTree | Observable<boolean | UrlTree> | Promise<boolean | UrlTree> {
    const token = this.authService.getToken();
    
    if (token && this.authService.isAuthenticated()) {
      return true;
    }
    
    // Token yoksa veya expire olduysa login'e yönlendir
    return this.router.createUrlTree(['/login']);
  }
}