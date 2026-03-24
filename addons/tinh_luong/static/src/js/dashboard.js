odoo.define('tinh_luong.DashboardAction', function (require) {
"use strict";

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var rpc = require('web.rpc');

var TinhLuongDashboard = AbstractAction.extend({
    template: 'TinhLuongDashboardMain',
    
    // Pagination config
    ITEMS_PER_PAGE: 10,
    current_page: 1,

    init: function(parent, context) {
        this._super(parent, context);
        this.kpi_data = {};
        this.chart_data = {};
        this.history_data = [];
        this.current_page = 1;
    },

    willStart: function() {
        var self = this;
        return $.when(this._super.apply(this, arguments), this.fetch_data());
    },

    start: function() {
        var self = this;
        return this._super().then(function() {
            self.render_charts();
            self.render_history();
            self.bind_pagination_events();
        });
    },

    fetch_data: function() {
        var self = this;
        return rpc.query({
            model: 'tinh_luong.dashboard',
            method: 'get_dashboard_data',
        }).then(function(result) {
            self.kpi_data = result.kpi || {};
            self.chart_data = result.charts || {};
            self.history_data = result.history || [];
        });
    },

    render_charts: function() {
        var self = this;
        
        if (typeof Chart === 'undefined') {
            console.error("Chart.js is not loaded.");
            return;
        }

        var ctxLine = this.$('#salaryTrendChart');
        if (ctxLine.length) {
            new Chart(ctxLine[0], {
                type: 'line',
                data: {
                    labels: self.chart_data.trend.labels,
                    datasets: [
                        { 
                            label: 'Lương thực nhận (VNĐ)', 
                            data: self.chart_data.trend.salary, 
                            borderColor: '#007bff',
                            backgroundColor: 'rgba(0,123,255,0.1)',
                            fill: true,
                            tension: 0.3
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        yAxes: [{
                            ticks: {
                                beginAtZero: true
                            }
                        }]
                    }
                }
            });
        }

        var ctxDoughnut = this.$('#statusDoughnutChart');
        if (ctxDoughnut.length) {
            new Chart(ctxDoughnut[0], {
                type: 'doughnut',
                data: {
                    labels: self.chart_data.doughnut_status.labels,
                    datasets: [{
                        data: self.chart_data.doughnut_status.data,
                        backgroundColor: ['#6c757d', '#28a745', '#17a2b8'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutoutPercentage: 70,
                    legend: { position: 'bottom' }
                }
            });
        }
    },

    formatCurrency: function(value) {
        if (!value) return "0 ₫";
        return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(value);
    },

    render_history: function() {
        var self = this;
        var $tbody = this.$('#historyTableBody');
        if (!$tbody.length) return;

        var statusColors = {
            'chua_duyet': '#6c757d',
            'da_duyet': '#28a745',
            'da_thanh_toan': '#17a2b8',
        };

        var total = self.history_data.length;
        var totalPages = Math.ceil(total / self.ITEMS_PER_PAGE) || 1;
        
        if (self.current_page > totalPages) self.current_page = totalPages;
        if (self.current_page < 1) self.current_page = 1;

        var start = (self.current_page - 1) * self.ITEMS_PER_PAGE;
        var end = Math.min(start + self.ITEMS_PER_PAGE, total);
        var pageData = self.history_data.slice(start, end);

        var html = '';
        _.each(pageData, function(row, idx) {
            var color = statusColors[row.trang_thai_key] || '#6c757d';
            var formatted_luong = self.formatCurrency(row.tong_luong);
            
            html += '<tr>' +
                '<td>' + (start + idx + 1) + '</td>' +
                '<td><strong>' + _.escape(row.ma_bang_luong) + '</strong></td>' +
                '<td><strong>' + _.escape(row.nhan_vien) + '</strong></td>' +
                '<td>' + _.escape(row.ky_luong) + '</td>' +
                '<td class="text-right">' + _.escape(formatted_luong) + '</td>' +
                '<td class="text-center"><span class="badge" style="background-color:' + color + ';color:#fff;padding:5px 10px;border-radius:12px;">' + _.escape(row.trang_thai) + '</span></td>' +
                '</tr>';
        });

        if (!total) {
            html = '<tr><td colspan="6" class="text-center text-muted p-4">Chưa có dữ liệu phiếu lương</td></tr>';
        }

        $tbody.html(html);

        this.$('.page-info').text('Trang ' + self.current_page + ' / ' + totalPages + ' (' + total + ' bản ghi)');
        this.$('.btn-prev-page').prop('disabled', self.current_page <= 1);
        this.$('.btn-next-page').prop('disabled', self.current_page >= totalPages);
    },

    bind_pagination_events: function() {
        var self = this;
        this.$('.btn-prev-page').on('click', function() {
            if (self.current_page > 1) {
                self.current_page--;
                self.render_history();
            }
        });
        this.$('.btn-next-page').on('click', function() {
            var totalPages = Math.ceil(self.history_data.length / self.ITEMS_PER_PAGE) || 1;
            if (self.current_page < totalPages) {
                self.current_page++;
                self.render_history();
            }
        });
    }
});

core.action_registry.add('tinh_luong_dashboard', TinhLuongDashboard);

return TinhLuongDashboard;

});
