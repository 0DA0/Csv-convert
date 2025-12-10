// Global değişkenler
let csvData = null;

// DOM elementleri
const csvFileInput = document.getElementById('csv_file');
const fileLabel = document.querySelector('.compact-file-label');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const rowCount = document.getElementById('rowCount');

// Filtre elementleri
const columnSelector = document.getElementById('columnSelector');
const projectSelect = document.getElementById('projectSelect');
const clientSelect = document.getElementById('clientSelect');
const userSelect = document.getElementById('userSelect');
const dataPreview = document.getElementById('dataPreview');

// ============== Dosya Yükleme ==============

csvFileInput.addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (!file) return;

    fileName.textContent = file.name;
    
    // CSV'yi parse et
    Papa.parse(file, {
        header: true,
        skipEmptyLines: true,
        complete: function(results) {
            csvData = results.data;
            rowCount.textContent = csvData.length;
            fileInfo.style.display = 'flex';
            
            // Filtreleri doldur
            populateFilters();
            
            // Önizleme oluştur
            createPreview();
        },
        error: function(error) {
            alert('Error parsing CSV: ' + error.message);
        }
    });
});

// Drag & Drop
fileLabel.addEventListener('dragover', (e) => {
    e.preventDefault();
    fileLabel.style.borderColor = '#667eea';
    fileLabel.style.background = '#eef2ff';
});

fileLabel.addEventListener('dragleave', (e) => {
    e.preventDefault();
    fileLabel.style.borderColor = '#cbd5e0';
    fileLabel.style.background = '#f7fafc';
});

fileLabel.addEventListener('drop', (e) => {
    e.preventDefault();
    fileLabel.style.borderColor = '#cbd5e0';
    fileLabel.style.background = '#f7fafc';
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        const file = files[0];
        if (file && file.name.endsWith('.csv')) {
            csvFileInput.files = files;
            csvFileInput.dispatchEvent(new Event('change'));
        } else {
            alert('Please upload a CSV file.');
        }
    }
});

// ============== Filtreleri Doldur ==============

function populateFilters() {
    if (!csvData || csvData.length === 0) return;

    // Kolonları al
    const columns = Object.keys(csvData[0]);
    
    // Kolon seçici
    columnSelector.innerHTML = '';
    columns.forEach(col => {
        const label = document.createElement('label');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.name = 'selected_columns[]';
        checkbox.value = col;
        checkbox.checked = true;
        
        label.appendChild(checkbox);
        label.appendChild(document.createTextNode(' ' + col));
        columnSelector.appendChild(label);
        
        // Event listener ekle
        checkbox.addEventListener('change', updatePreview);
    });

    // Benzersiz değerleri çıkar
    const projects = new Set();
    const clients = new Set();
    const users = new Set();

    csvData.forEach(row => {
        if (row['Project'] && row['Project'].trim()) projects.add(row['Project'].trim());
        if (row['Client'] && row['Client'].trim()) clients.add(row['Client'].trim());
        if (row['User'] && row['User'].trim()) users.add(row['User'].trim());
    });

    // Seçenekleri doldur
    populateSelect(projectSelect, projects);
    populateSelect(clientSelect, clients);
    populateSelect(userSelect, users);
}

function populateSelect(selectElement, values) {
    // "All" seçeneğini koru
    const allOption = selectElement.querySelector('option[value=""]');
    selectElement.innerHTML = '';
    if (allOption) {
        selectElement.appendChild(allOption.cloneNode(true));
    }

    // Sıralı şekilde ekle
    const sortedValues = Array.from(values).sort();
    sortedValues.forEach(value => {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = value;
        selectElement.appendChild(option);
    });
}

// ============== Önizleme Oluştur ==============

function createPreview() {
    if (!csvData || csvData.length === 0) {
        dataPreview.innerHTML = `
            <div class="preview-placeholder">
                <svg width="64" height="64" fill="none" stroke="currentColor" stroke-width="1">
                    <path d="M9 12h6m-6 4h6m-6 4h6m9-10h6m-6 4h6m-6 4h6M9 5a2 2 0 00-2 2v10a2 2 0 002 2h14a2 2 0 002-2V7a2 2 0 00-2-2H9z"/>
                </svg>
                <p>No data to preview</p>
            </div>
        `;
        return;
    }

    updatePreview();
}

// ============== Gerçek Zamanlı Filtreleme ==============

const filterSelects = [projectSelect, clientSelect, userSelect];
filterSelects.forEach(select => {
    select.addEventListener('change', updatePreview);
});

function updatePreview() {
    if (!csvData || csvData.length === 0) return;

    // Seçili filtreleri al
    const selectedProjects = Array.from(projectSelect.selectedOptions)
        .map(opt => opt.value)
        .filter(v => v !== '');
    
    const selectedClients = Array.from(clientSelect.selectedOptions)
        .map(opt => opt.value)
        .filter(v => v !== '');
    
    const selectedUsers = Array.from(userSelect.selectedOptions)
        .map(opt => opt.value)
        .filter(v => v !== '');

    // Seçili kolonları al
    const selectedColumns = Array.from(document.querySelectorAll('#columnSelector input:checked'))
        .map(cb => cb.value);

    if (selectedColumns.length === 0) {
        dataPreview.innerHTML = '<div class="preview-placeholder"><p>Please select at least one column</p></div>';
        return;
    }

    // Veriyi filtrele
    let filteredData = csvData;

    if (selectedProjects.length > 0) {
        filteredData = filteredData.filter(row => 
            selectedProjects.includes(row['Project'])
        );
    }

    if (selectedClients.length > 0) {
        filteredData = filteredData.filter(row => 
            selectedClients.includes(row['Client'])
        );
    }

    if (selectedUsers.length > 0) {
        filteredData = filteredData.filter(row => 
            selectedUsers.includes(row['User'])
        );
    }

    // Önizlemeyi güncelle
    if (filteredData.length === 0) {
        dataPreview.innerHTML = '<div class="preview-placeholder"><p>No data matches the selected filters</p></div>';
        return;
    }

    const previewData = filteredData.slice(0, 15); // İlk 15 satır

    let html = '<table class="preview-table-full"><thead><tr>';
    
    selectedColumns.forEach(col => {
        html += `<th>${escapeHtml(col)}</th>`;
    });
    
    html += '</tr></thead><tbody>';

    previewData.forEach(row => {
        html += '<tr>';
        selectedColumns.forEach(col => {
            const value = row[col] || '';
            html += `<td title="${escapeHtml(value)}">${escapeHtml(value)}</td>`;
        });
        html += '</tr>';
    });

    html += `</tbody></table>`;
    html += `<p style="margin-top: 16px; font-size: 13px; color: #718096; text-align: center; padding: 0 8px;">
        Showing ${previewData.length} of ${filteredData.length} filtered rows (${csvData.length} total)
    </p>`;
    
    dataPreview.innerHTML = html;
}

// ============== Yardımcı Fonksiyonlar ==============

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, m => map[m]);
}

// ============== Form Gönderimi ==============

const uploadForm = document.getElementById('uploadForm');
if (uploadForm) {
    uploadForm.addEventListener('submit', function(e) {
        const submitBtn = this.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = `
                <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" class="spinning">
                    <circle cx="10" cy="10" r="8"></circle>
                    <path d="M20 10a10 10 0 0 1-10 10"></path>
                </svg>
                Generating Report...
            `;
            
            // Timeout ile reset (hata durumunda)
            setTimeout(() => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }, 30000);
        }
    });
}

// Spin animasyonu
const style = document.createElement('style');
style.textContent = `
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    .spinning {
        animation: spin 1s linear infinite;
        display: inline-block;
    }
`;
document.head.appendChild(style);