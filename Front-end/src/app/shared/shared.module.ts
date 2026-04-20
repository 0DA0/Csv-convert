import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatMenuModule } from '@angular/material/menu';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBarModule } from '@angular/material/snack-bar';

import { HeaderComponent } from './components/header/header.component';
import { ReportPreviewComponent } from './components/report-preview/report-preview.component';

const MATERIAL_MODULES = [
  MatButtonModule, MatIconModule, MatToolbarModule, MatMenuModule,
  MatCardModule, MatFormFieldModule, MatInputModule, MatSelectModule,
  MatTableModule, MatProgressSpinnerModule, MatSnackBarModule
];

@NgModule({
  declarations: [
    HeaderComponent,
    ReportPreviewComponent
  ],
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    ...MATERIAL_MODULES
  ],
  exports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    HeaderComponent,
    ReportPreviewComponent,
    ...MATERIAL_MODULES
  ]
})
export class SharedModule { }