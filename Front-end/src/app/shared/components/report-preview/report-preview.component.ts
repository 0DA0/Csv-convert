import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-report-preview',
  templateUrl: './report-preview.component.html',
  styleUrls: ['./report-preview.component.scss']
})
export class ReportPreviewComponent {
  @Input() previewData: any = null;

  summaryOpen  = true;   // Summary varsayılan açık
  detailedOpen = false;  // Detailed varsayılan kapalı

  getSummaryShown(): number {
    if (!this.previewData?.summary?.users) return 0;
    return this.previewData.summary.users.reduce(
      (sum: number, u: any) => sum + (u.rows_shown || 0), 0
    );
  }

  getDetailedShown(): number {
    if (!this.previewData?.detailed?.users) return 0;
    return this.previewData.detailed.users.reduce(
      (sum: number, u: any) => sum + (u.rows_shown || 0), 0
    );
  }

  isSummaryTruncated(): boolean {
    return this.getSummaryShown() < (this.previewData?.summary?.total_rows || 0);
  }

  isDetailedTruncated(): boolean {
    return this.getDetailedShown() < (this.previewData?.detailed?.total_rows || 0);
  }
}