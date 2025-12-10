// Global değişkenler
let csvData = null;
let currentStep = 1;

// DOM elementleri
const csvFileInput = document.getElementById('csv_file');
const fileLabel = document.querySelector('.file-label');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const rowCount = document.getElementById('rowCount');

// Adım butonları
const nextToSchema = document.getElementById('nextToSchema');
const nextToFilters = document.getElementById('nextToFilters');
const backToFile = document.getElementById('backToFile');
const backToSchema = document.getElementById('backToSchema');

// Adım bölümleri
const step1 = document.getElementById('step1');
const step2 = document.getElementById('step2');
const step3 = document.getElementById('step3');

// Schema kartları
const schemaCards = document.querySelectorAll('.schema-card');
const schemaRadios = document.querySelectorAll('input[name="schema_choice"]');

// Filtre elementleri
const columnSelector = document.getElementById('columnSelector');
const projectSelect = document.getElementById('projectSelect');
const clientSelect = document.getElementById('clientSelect');
const userSelect = document.getElementById('userSelect');
const dataPreview = document.getElementById('dataPreview');

// Tab elementleri
const filterTabs = document.querySelectorAll('.filter-tab');
const filterContents = document.querySelectorAll('.filter-content');

// ============== Tab Sistemi ==============

filterTabs.forEach(tab => {
    tab.addEventListener('click', () => {
        const targetTab = tab.dataset.tab;
        
        // Tüm tabları pasif yap
        filterTabs.forEach(t => t.classList.remove('active'));
        filterContents.forEach(c => c.classList.remove('active'));
        
        // Seçili tabı aktif yap
        tab.classList.add('active');
        document.getElementById(`tab-${targetTab}`).classList.add('active');
    });
});

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
            fileInfo.style.display = 'block';
            
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
    fileLabel.style.transform = 'scale(1.02)';
});

fileLabel.addEventListener('dragleave', (e) => {
    e.preventDefault();
    fileLabel.style.borderColor = '#cbd5e0';
    fileLabel.style.transform = 'scale(1)';
});

fileLabel.addEventListener('drop', (e) => {
    e.preventDefault();
    fileLabel.style.borderColor = '#cbd5e0';
    fileLabel.style.transform = 'scale(1)';
    
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

// ============== Adım Navigasyonu ==============

nextToSchema.addEventListener('click', () => {
    if (!csvFileInput.files.length) {
        alert('Please upload a CSV file first.');
        return;
    }
    navigateToStep(2);
});

nextToFilters.addEventListener('click', () => {
    navigateToStep(3);
});

backToFile.addEventListener('click', () => {
    navigateToStep(1);
});

backToSchema.addEventListener('click', () => {
    navigateToStep(2);
});

function navigateToStep(step) {
    currentStep = step;
    
    step1.classList.remove('active');
    step2.classList.remove('active');
    step3.classList.remove('active');
    
    if (step === 1) step1.classList.add('active');
    else if (step === 2) step2.classList.add('active');
    else if (step === 3) step3.classList.add('active');
    
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ============== Schema Seçimi ==============

schemaCards.forEach(card => {
    card.addEventListener('click', () => {
        const schema = card.dataset.schema;
        const radio = card.querySelector('input[type="radio"]');
        
        schemaCards.forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
        
        radio.checked = true;
        document.getElementById('selectedSchema').value = schema;
    });
});

schemaRadios.forEach(radio => {
    radio.addEventListener('change', () => {
        const schema = radio.value;
        document.getElementById('selectedSchema').value = schema;
        
        schemaCards.forEach(card => {
            if (card.dataset.schema === schema) {
                card.classList.add('selected');
            } else {
                card.classList.remove('selected');
            }
        });
    });
});

// İlk schema'yı seç
const classicCard = document.querySelector('.schema-card[data-schema="classic"]');
if (classicCard) {
    classicCard.classList.add('selected');
}

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
        dataPreview.innerHTML = '<p class="preview-placeholder">No data to preview</p>';
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
        dataPreview.innerHTML = '<p class="preview-placeholder">Please select at least one column</p>';
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
        dataPreview.innerHTML = '<p class="preview-placeholder">No data matches the selected filters</p>';
        return;
    }

    const previewData = filteredData.slice(0, 20); // İlk 20 satır

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
    html += `<p style="margin-top: 20px; font-size: 14px; color: #718096; text-align: center;">
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