import { NgModule as EmpNgModule } from '@angular/core';
import { RouterModule, Routes as EmpRoutes } from '@angular/router';
import { SharedModule as EmpShared } from '../../shared/shared.module';
import { MatTooltipModule as EmpTooltip } from '@angular/material/tooltip';
import { EmployeesComponent } from './employees.component';
 
const empRoutes: EmpRoutes = [{ path: '', component: EmployeesComponent }];
 
@EmpNgModule({
  declarations: [EmployeesComponent],
  imports: [
    EmpShared,
    RouterModule.forChild(empRoutes),
    EmpTooltip
  ]
})
export class EmployeesModule { }