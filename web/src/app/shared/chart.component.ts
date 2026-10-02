import { Component, ElementRef, Input, OnChanges, OnDestroy, ViewChild } from '@angular/core';
import { Chart, ChartConfiguration, registerables } from 'chart.js';

Chart.register(...registerables);

@Component({
  selector: 'app-chart',
  standalone: true,
  template: `<div class="box"><canvas #canvas></canvas></div>`,
  styles: [`.box { position: relative; height: 260px; }`],
})
export class ChartComponent implements OnChanges, OnDestroy {
  @Input({ required: true }) config!: ChartConfiguration;
  @ViewChild('canvas', { static: true }) canvas!: ElementRef<HTMLCanvasElement>;
  private chart?: Chart;

  ngOnChanges() {
    this.chart?.destroy();
    this.chart = new Chart(this.canvas.nativeElement, {
      ...this.config,
      options: { responsive: true, maintainAspectRatio: false, ...this.config.options },
    });
  }

  ngOnDestroy() { this.chart?.destroy(); }
}
