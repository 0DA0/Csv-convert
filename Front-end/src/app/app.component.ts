import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router'; // 1. Bunu ekle

@Component({
  selector: 'app-root',
  standalone: true, // Eğer burası true ise
  imports: [RouterOutlet], // 2. Buraya RouterOutlet ekle
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent {
  title = 'Front-end';
}