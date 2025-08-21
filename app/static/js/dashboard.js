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
            // Don't initialize DataTables to avoid conflicts with custom pagination
            // Just add sorting handlers directly
            addSortingHandlers(tableId);
        }
    });

    // Connect search and filter controls
    setupTableControls();
}

// Add sorting click handlers to table headers
function addSortingHandlers(tableId) {
    const table = document.getElementById(tableId);
    const sortableHeaders = table.querySelectorAll('thead th.sortable');

    sortableHeaders.forEach(header => {
        const column = header.getAttribute('data-column');
        if (column) {
            header.style.cursor = 'pointer';
            
            header.addEventListener('click', () => {
                const currentSort = new URLSearchParams(window.location.search).get('sort_column');
                const currentDirection = new URLSearchParams(window.location.search).get('sort_direction') || 'asc';
                
                let newDirection = 'asc';
                if (currentSort === column && currentDirection === 'asc') {
                    newDirection = 'desc';
                }
                
                // Update URL without reload
                const params = new URLSearchParams(window.location.search);
                params.set('sort_column', column);
                params.set('sort_direction', newDirection);
                params.set('page', '1'); // Reset to first page
                
                // Update browser URL
                const newUrl = '/dashboard?' + params.toString();
                window.history.pushState({}, '', newUrl);
                
                // Reload table data via AJAX
                loadTableData();
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
            const params = new URLSearchParams(window.location.search);
            if (searchTerm) {
                params.set('search', searchTerm);
            } else {
                params.delete('search');
            }
            params.set('page', '1');
            
            // Update URL without reload
            const newUrl = '/dashboard?' + params.toString();
            window.history.pushState({}, '', newUrl);
            
            // Reload table and summary data
            loadTableData();
            loadSummaryData();
        }, 500);
    });

    // Namespace filter
    $('#namespaceFilter').on('change', function() {
        const selectedNamespace = this.value;
        const params = new URLSearchParams(window.location.search);
        if (selectedNamespace === 'all') {
            params.delete('namespace');
        } else {
            params.set('namespace', selectedNamespace);
        }
        params.set('page', '1');
        
        // Update URL without reload
        const newUrl = '/dashboard?' + params.toString();
        window.history.pushState({}, '', newUrl);
        
        // Reload table and summary data
        loadTableData();
        loadSummaryData();
    });

    // Hide incomplete data filter
    $('#hideIncompleteData').on('change', function() {
        const isChecked = this.checked;
        const params = new URLSearchParams(window.location.search);
        if (isChecked) {
            params.set('hide_incomplete', 'true');
        } else {
            params.delete('hide_incomplete');
        }
        params.set('page', '1');
        
        // Update URL without reload
        const newUrl = '/dashboard?' + params.toString();
        window.history.pushState({}, '', newUrl);
        
        // Reload table and summary data
        loadTableData();
        loadSummaryData();
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
                fill: false,
                tension: 0.1,
                yAxisID: 'y'
            }, {
                label: 'vs Requests (%)',
                data: [],
                borderColor: 'rgba(54, 162, 235, 1)',
                backgroundColor: 'rgba(54, 162, 235, 0.1)',
                borderWidth: 2,
                fill: false,
                tension: 0.1,
                yAxisID: 'y1'
            }, {
                label: 'vs Limits (%)',
                data: [],
                borderColor: 'rgba(255, 206, 86, 1)',
                backgroundColor: 'rgba(255, 206, 86, 0.1)',
                borderWidth: 2,
                fill: false,
                tension: 0.1,
                yAxisID: 'y1'
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
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'CPU Cores'
                    },
                    beginAtZero: true
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Percentage (%)'
                    },
                    beginAtZero: true,
                    grid: {
                        drawOnChartArea: false,
                    },
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
                label: 'Memory Usage (GB)',
                data: [],
                borderColor: 'rgba(75, 192, 192, 1)',
                backgroundColor: 'rgba(75, 192, 192, 0.1)',
                borderWidth: 2,
                fill: false,
                tension: 0.1,
                yAxisID: 'y'
            }, {
                label: 'vs Requests (%)',
                data: [],
                borderColor: 'rgba(153, 102, 255, 1)',
                backgroundColor: 'rgba(153, 102, 255, 0.1)',
                borderWidth: 2,
                fill: false,
                tension: 0.1,
                yAxisID: 'y1'
            }, {
                label: 'vs Limits (%)',
                data: [],
                borderColor: 'rgba(255, 159, 64, 1)',
                backgroundColor: 'rgba(255, 159, 64, 0.1)',
                borderWidth: 2,
                fill: false,
                tension: 0.1,
                yAxisID: 'y1'
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
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Memory (GB)'
                    },
                    beginAtZero: true
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Percentage (%)'
                    },
                    beginAtZero: true,
                    grid: {
                        drawOnChartArea: false,
                    },
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
        const response = await fetch('/api/chart-data?hours=24');
        if (!response.ok) throw new Error('Failed to fetch chart data');

        const data = await response.json();

        // Update CPU chart
        cpuChart.data.labels = data.timestamps;
        cpuChart.data.datasets[0].data = data.cpu_usage_absolute;
        cpuChart.data.datasets[1].data = data.cpu_usage_percentage_requests;
        cpuChart.data.datasets[2].data = data.cpu_usage_percentage_limits;
        cpuChart.update('none');

        // Update Memory chart
        memoryChart.data.labels = data.timestamps;
        memoryChart.data.datasets[0].data = data.memory_usage_absolute;
        memoryChart.data.datasets[1].data = data.memory_usage_percentage_requests;
        memoryChart.data.datasets[2].data = data.memory_usage_percentage_limits;
        memoryChart.update('none');

    } catch (error) {
        console.error('Error loading chart data:', error);
    }
}

// Load summary data via AJAX
async function loadSummaryData() {
    try {
        const params = new URLSearchParams(window.location.search);
        const url = `/api/summary?${params.toString()}`;
        
        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to fetch summary data');
        
        const data = await response.json();
        
        // Update summary cards
        updateSummaryCards(data);
        
    } catch (error) {
        console.error('Error loading summary data:', error);
    }
}

// Update summary cards with new data
function updateSummaryCards(data) {
    // Find and update each card
    const cards = document.querySelectorAll('.card-text');
    if (cards.length >= 8) {
        cards[0].textContent = data.total_cpu_requests.toFixed(1);
        cards[1].textContent = data.total_cpu_limits.toFixed(1);
        cards[2].textContent = data.total_memory_requests_gb.toFixed(1);
        cards[3].textContent = data.total_memory_limits_gb.toFixed(1);
        cards[4].textContent = data.total_cpu_usage.toFixed(1);
        cards[5].textContent = data.total_memory_usage_gb.toFixed(1);
        cards[6].textContent = data.cpu_requests_underutilization.toFixed(1);
        cards[7].textContent = data.memory_requests_underutilization_gb.toFixed(1);
    }
}

// Load table data via AJAX (currently loads all tables at once)
async function loadTableData() {
    try {
        const params = new URLSearchParams(window.location.search);
        
        // For now, reload the entire page content
        // In a full implementation, you'd load each table separately
        const url = `/dashboard?${params.toString()}`;
        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to fetch table data');
        
        const html = await response.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        // Update table content
        const tables = ['cpuRequestsTable', 'cpuLimitsTable', 'memoryRequestsTable', 'memoryLimitsTable'];
        tables.forEach(tableId => {
            const oldTable = document.getElementById(tableId);
            const newTable = doc.getElementById(tableId);
            if (oldTable && newTable) {
                oldTable.innerHTML = newTable.innerHTML;
            }
        });
        
        // Update pagination
        const oldPagination = document.querySelector('.pagination');
        const newPagination = doc.querySelector('.pagination');
        if (oldPagination && newPagination) {
            oldPagination.innerHTML = newPagination.innerHTML;
            // Add click handlers to new pagination links
            addPaginationHandlers();
        }
        
        // Re-add sorting handlers to new table headers
        const tableConfigs = {
            'cpuRequestsTable': 'CPU Requests vs Usage',
            'cpuLimitsTable': 'CPU Limits vs Usage',
            'memoryRequestsTable': 'Memory Requests vs Usage',
            'memoryLimitsTable': 'Memory Limits vs Usage'
        };
        
        Object.keys(tableConfigs).forEach(tableId => {
            if (document.getElementById(tableId)) {
                addSortingHandlers(tableId);
            }
        });
        
    } catch (error) {
        console.error('Error loading table data:', error);
    }
}

// Add pagination click handlers
function addPaginationHandlers() {
    const paginationLinks = document.querySelectorAll('.pagination .page-link');
    
    paginationLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const href = this.getAttribute('href');
            if (href && href !== '#') {
                // Extract page number from href
                const url = new URL(href, window.location.origin);
                const params = new URLSearchParams(url.search);
                
                // Update current URL
                const currentParams = new URLSearchParams(window.location.search);
                const page = params.get('page');
                if (page) {
                    currentParams.set('page', page);
                    
                    // Update browser URL
                    const newUrl = '/dashboard?' + currentParams.toString();
                    window.history.pushState({}, '', newUrl);
                    
                    // Reload table data
                    loadTableData();
                }
            }
        });
    });
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