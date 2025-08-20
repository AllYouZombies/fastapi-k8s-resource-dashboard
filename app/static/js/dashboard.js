let cpuChart, memoryChart;
let tables = {};

// Initialize DataTables for all resource tables
function initializeTables() {
    const tableConfigs = {
        'cpuRequestsTable': 'CPU Requests vs Usage',
        'cpuLimitsTable': 'CPU Limits vs Usage',
        'memoryRequestsTable': 'Memory Requests vs Usage',
        'memoryLimitsTable': 'Memory Limits vs Usage'
    };

    Object.keys(tableConfigs).forEach(tableId => {
        if (document.getElementById(tableId)) {
            tables[tableId] = $(`#${tableId}`).DataTable({
                pageLength: 20,
                lengthMenu: [[10, 20, 50, 100, -1], [10, 20, 50, 100, "All"]],
                searching: true,
                ordering: true,
                order: [[0, 'asc']],
                stateSave: true,
                stateDuration: 60 * 60,
                responsive: true,
                columnDefs: [
                    {
                        targets: [3, 4, 5], // Resource columns
                        type: "string"
                    }
                ],
                language: {
                    search: "Filter records:",
                    lengthMenu: "Show _MENU_ entries",
                    info: "Showing _START_ to _END_ of _TOTAL_ entries"
                }
            });
        }
    });

    // Connect search and filter controls
    setupTableControls();
}

function setupTableControls() {
    // Pod name search
    $('#podSearch').on('keyup', function() {
        const searchTerm = this.value;
        Object.values(tables).forEach(table => {
            table.columns(0).search(searchTerm).draw();
        });
    });

    // Namespace filter
    $('#namespaceFilter').on('change', function() {
        const selectedNamespace = this.value;
        const searchTerm = selectedNamespace === 'all' ? '' : selectedNamespace;
        Object.values(tables).forEach(table => {
            table.columns(1).search(searchTerm).draw();
        });

        // Update URL with new filter
        updateUrlParams({ namespace: selectedNamespace === 'all' ? null : selectedNamespace });
    });
}

// Initialize Chart.js charts
function initializeCharts() {
    // CPU Utilization Chart
    const cpuCtx = document.getElementById('cpuChart').getContext('2d');
    cpuChart = new Chart(cpuCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'CPU Usage (cores)',
                data: [],
                borderColor: 'rgba(255, 99, 132, 1)',
                backgroundColor: 'rgba(255, 99, 132, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Time'
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: 'CPU Cores'
                    },
                    beginAtZero: true
                }
            }
        }
    });

    // Memory Utilization Chart
    const memoryCtx = document.getElementById('memoryChart').getContext('2d');
    memoryChart = new Chart(memoryCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Memory Usage (MB)',
                data: [],
                borderColor: 'rgba(54, 162, 235, 1)',
                backgroundColor: 'rgba(54, 162, 235, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Time'
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Memory (MB)'
                    },
                    beginAtZero: true
                }
            }
        }
    });

    // Load initial chart data
    loadChartData();
}

// Load and update chart data
async function loadChartData() {
    try {
        const response = await fetch('/api/chart-data');
        if (!response.ok) throw new Error('Failed to fetch chart data');

        const data = await response.json();

        // Update CPU chart
        cpuChart.data.labels = data.timestamps;
        cpuChart.data.datasets[0].data = data.cpu_utilization;
        cpuChart.update('none');

        // Update Memory chart
        memoryChart.data.labels = data.timestamps;
        memoryChart.data.datasets[0].data = data.memory_utilization;
        memoryChart.update('none');

    } catch (error) {
        console.error('Error loading chart data:', error);
    }
}

// Auto-refresh functionality
let refreshInterval;

function startAutoRefresh() {
    // Refresh every 5 minutes (300000ms)
    refreshInterval = setInterval(() => {
        refreshData();
    }, 300000);
}

function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

async function refreshData() {
    try {
        // Show loading indicator
        showLoadingState();

        // Reload the page data
        const currentUrl = new URL(window.location);
        const response = await fetch(currentUrl.pathname + currentUrl.search);

        if (!response.ok) throw new Error('Failed to refresh data');

        // For now, we'll just reload the page
        // In a production app, you'd want to update data without full reload
        location.reload();

    } catch (error) {
        console.error('Error refreshing data:', error);
        showErrorMessage('Failed to refresh data');
    } finally {
        hideLoadingState();
    }
}

function showLoadingState() {
    document.querySelector('button[onclick="refreshData()"]').innerHTML =
        '<i class="fas fa-spinner fa-spin"></i> Refreshing...';
}

function hideLoadingState() {
    document.querySelector('button[onclick="refreshData()"]').innerHTML =
        '<i class="fas fa-sync-alt"></i> Refresh';
}

function showErrorMessage(message) {
    // Create toast notification
    const toast = document.createElement('div');
    toast.className = 'toast align-items-center text-white bg-danger border-0';
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;

    // Add to page and show
    document.body.appendChild(toast);
    const bootstrapToast = new bootstrap.Toast(toast);
    bootstrapToast.show();

    // Remove after hiding
    toast.addEventListener('hidden.bs.toast', () => {
        document.body.removeChild(toast);
    });
}

function updateUrlParams(params) {
    const url = new URL(window.location);
    Object.keys(params).forEach(key => {
        if (params[key] === null || params[key] === undefined) {
            url.searchParams.delete(key);
        } else {
            url.searchParams.set(key, params[key]);
        }
    });
    window.history.replaceState({}, '', url);
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    stopAutoRefresh();
});