import { Injectable } from '@angular/core';
import { ActivatedRouteSnapshot, Router, UrlTree } from '@angular/router';
import { AuthService } from '../services/auth.service';
 
@Injectable({ providedIn: 'root' })
export class RoleGuard {
  constructor(private authService: AuthService, private router: Router) {}
 
  canActivate(route: ActivatedRouteSnapshot): boolean | UrlTree {
    const allowedRoles: string[] = route.data?.['roles'] || [];
    const user = this.authService.getCurrentUser();
    if (user && allowedRoles.includes(user.user_type)) return true;
    return this.router.createUrlTree(['/dashboard']);
  }
}