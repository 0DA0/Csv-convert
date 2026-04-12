import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
 
@Component({
  selector: 'app-header',
  templateUrl: './header.component.html',
  styleUrls: ['./header.component.scss']
})
export class HeaderComponent {
  constructor(public authService: AuthService, private router: Router) {}
 
  get userType(): string { return this.authService.getCurrentUser()?.user_type || ''; }
 
  navigateToDashboard(): void {
    if (this.userType === 'employee') this.router.navigate(['/employee']);
    else this.router.navigate(['/dashboard']);
  }
  navigateToProfile():   void { this.router.navigate(['/profile']); }
  navigateToInvoice():   void { this.router.navigate(['/invoice']); }
  navigateToEmployees(): void { this.router.navigate(['/employees']); }
  logout(): void { this.authService.logout(); }
}
