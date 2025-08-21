let cpuChart, memoryChart;
let tables = {};

// Initialize tables with server-side sorting
function initializeTables() {
    const tableConfigs = {
        'cpuRequestsTable': 'CPU Requests vs Usage',
        'cpuLimitsTable': 'CPU Limits vs Usage',
        'memoryRequestsTable': 'Memory Requests vs Usage',
        'memoryLimitsTable': 'Memory Limits vs Usage'
    };

    Object.keys(tableConfigs).forEach(tableId => {
        if (document.getElementById(tableId)) {
            // Disable DataTables sorting and use server-side sorting instead
            tables[tableId] = $(`#${tableId}`).DataTable({
                paging: false,
                searching: false,
                ordering: false,
                info: false,
                responsive: true,
                language: {
                    emptyTable: "No data available"
                }
            });
            
            // Add click handlers for column headers
            addSortingHandlers(tableId);
        }
    });

    // Connect search and filter controls
    setupTableControls();
}

// Add sorting click handlers to table headers
function addSortingHandlers(tableId) {
    const table = document.getElementById(tableId);
    const headers = table.querySelectorAll('thead th');
    
    const columnMappings = {
        0: 'pod_name',
        1: 'namespace', 
        2: 'container_name',
        3: 'cpu_request_cores', // For requests tables
        4: 'cpu_usage_cores',
        5: null, // Utilization % is calculated
        6: 'pod_phase',
        7: 'node_name'
    };
    
    // Adjust mapping for limits tables
    if (tableId.includes('Limits')) {
        if (tableId.includes('cpu')) {
            columnMappings[3] = 'cpu_limit_cores';
        } else {
            columnMappings[3] = 'memory_limit_bytes';
        }
    } else if (tableId.includes('memory')) {
        columnMappings[3] = 'memory_request_bytes';
        columnMappings[4] = 'memory_usage_bytes';
    }

    headers.forEach((header, index) => {
        const column = columnMappings[index];
        if (column) {
            header.style.cursor = 'pointer';
            header.innerHTML += ' <i class="fas fa-sort"></i>';
            
            header.addEventListener('click', () => {
                const url = new URL(window.location);
                const currentSort = url.searchParams.get('sort_column');
                const currentDirection = url.searchParams.get('sort_direction') || 'asc';
                
                let newDirection = 'asc';
                if (currentSort === column && currentDirection === 'asc') {
                    newDirection = 'desc';
                }
                
                url.searchParams.set('sort_column', column);
                url.searchParams.set('sort_direction', newDirection);
                url.searchParams.set('page', '1'); // Reset to first page
                
                window.location = url.toString();
            });
        }
    });
}

function setupTableControls() {
    // Pod name search with debounce
    let searchTimeout;
    $('#podSearch').on('keyup', function() {
        const searchTerm = this.value;
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            updateUrlParams({ 
                search: searchTerm || null, 
                page: 1 
            });
            window.location.reload();
        }, 500);
    });

    // Namespace filter
    $('#namespaceFilter').on('change', function() {
        const selectedNamespace = this.value;
        updateUrlParams({ 
            namespace: selectedNamespace === 'all' ? null : selectedNamespace,
            page: 1 
        });
        window.location.reload();
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