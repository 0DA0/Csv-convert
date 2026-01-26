import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { InvoiceComponent } from './invoice.component';
import { SharedModule } from '../../shared/shared.module';

const routes: Routes = [
  { path: '', component: InvoiceComponent }
];

@NgModule({
  declarations: [
    InvoiceComponent
  ],
  imports: [
    SharedModule,
    RouterModule.forChild(routes)
  ]
})
export class InvoiceModule { }