odoo.define('cham_cong.DashboardAction', function (require) {
"use strict";

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var rpc = require('web.rpc');

var QWeb = core.qweb;

var ChamCongDashboard = AbstractAction.extend({
    template: 'ChamCongDashboardMain',
    
    init: function(parent, context) {
        this._super(parent, context);
        this.kpi_data = {};
        this.chart_data = {};
    },

    willStart: function() {
        var self = this;
        // Chờ fetch data xong mới render QWeb
        return $.when(this._super.apply(this, arguments), this.fetch_data());
    },

    start: function() {
        var self = this;
        return this._super().then(function() {
            // Sau khi giao diện render xong thì vẽ biểu đồ
            self.render_charts();
        });
    },

    fetch_data: function() {
        var self = this;
        return rpc.query({
            model: 'cham_cong.dashboard',
            method: 'get_dashboard_data',
        }).then(function(result) {
            self.kpi_data = result.kpi;
            self.chart_data = result.charts;
        });
    },

    render_charts: function() {
        var self = this;
        
        // Thư viện Chart.js thường được load sẵn trong Odoo bằng global variable `Chart`
        // Nếu dùng Chart.js version mới của Odoo 15:
        if (typeof Chart === 'undefined') {
            console.error("Chart.js is not loaded in this environment.");
            return;
        }

        // Render Bar Chart
        var ctxBar = this.$('#attendanceBarChart');
        if (ctxBar.length) {
            new Chart(ctxBar[0], {
                type: 'bar',
                data: {
                    labels: self.chart_data.bar.labels,
                    datasets: [
                        { label: 'Đi làm đúng giờ', data: self.chart_data.bar.on_time, backgroundColor: '#007bff' },
                        { label: 'Đi muộn/Về sớm', data: self.chart_data.bar.late, backgroundColor: '#ffc107' },
                        { label: 'Vắng mặt', data: self.chart_data.bar.absent, backgroundColor: '#dc3545' }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true, stacked: true },
                        x: { stacked: true }
                    }
                }
            });
        }

        // Render Doughnut Chart
        var ctxDoughnut = this.$('#leaveDoughnutChart');
        if (ctxDoughnut.length) {
            new Chart(ctxDoughnut[0], {
                type: 'doughnut',
                data: {
                    labels: self.chart_data.doughnut.labels,
                    datasets: [{
                        data: self.chart_data.doughnut.data,
                        backgroundColor: ['#ffc107', '#28a745', '#dc3545'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '70%',
                    plugins: {
                        legend: { position: 'bottom' }
                    }
                }
            });
        }
    }
});

// Đăng ký thẻ widget tag cham_cong_dashboard để gọi XML Action tương ứng
core.action_registry.add('cham_cong_dashboard', ChamCongDashboard);

return ChamCongDashboard;

});
