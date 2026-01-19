import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

// BU MODÜL ARTIK GEREKSİZ ÇÜNKÜ COMPONENT'LER APP.MODULE'DE DECLARE EDİLDİ
// Ama silmeyin, dashboard ve profile gibi modüller hala lazy loading kullanıyor

@NgModule({
  declarations: [],
  imports: [
    CommonModule
  ]
})
export class AuthModule { }