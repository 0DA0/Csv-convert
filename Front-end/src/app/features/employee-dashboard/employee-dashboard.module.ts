import { NgModule as EmployeeNgModule } from '@angular/core';
import { RouterModule, Routes as EmployeeRoutes } from '@angular/router';
import { SharedModule } from '../../shared/shared.module';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatTooltipModule } from '@angular/material/tooltip';
import { EmployeeDashboardComponent } from './employee-dashboard.component';

const employeeRoutes: EmployeeRoutes = [{ path: '', component: EmployeeDashboardComponent }];

@EmployeeNgModule({
  declarations: [EmployeeDashboardComponent],
  imports: [
    SharedModule,
    RouterModule.forChild(employeeRoutes),
    MatDatepickerModule,
    MatNativeDateModule,
    MatTooltipModule
  ]
})
export class EmployeeDashboardModule { }