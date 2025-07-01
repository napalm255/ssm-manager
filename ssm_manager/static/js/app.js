const app = {
    refreshInterval: null,
    refreshCountdown: 30,
    currentProfile: '',
    currentRegion: '',
    instances: [],
    connections: [],
    awsAccountId: null,
    elements: {},

    localTheme: 'lastTheme',
    localProfile: 'lastProfile',
    localRegion: 'lastRegion',

    modals: {},
    toasts: {},

    preferences: {
        startPort: 60000,
        endPort: 60255,
        logLevel: 'WARNING',
        regions: [],
        instances: []
    },

    async init() {
        console.log('Initializing application...');
        try {
            this.cacheElements();
            this.initializeComponents();
            this.setupEventListeners();
            this.loadTheme();
            await this.loadProfilesAndRegions();
            await this.loadLastUsedProfileAndRegion();
            this.checkConnections();
            this.startConnectionMonitoring();
            console.log('Application initialized successfully');
        } catch (error) {
            console.error('Error initializing application:', error);
        }

    },

    cacheElements() {
        console.log('Caching DOM elements...');
        this.elements = {
            profileSelect: document.getElementById('profileSelect'),
            regionSelect: document.getElementById('regionSelect'),
            regionsSelect: document.getElementById('regionsSelect'),
            connectBtn: document.getElementById('connectBtn'),
            refreshBtn: document.getElementById('refreshBtn'),
            autoRefreshSwitch: document.getElementById('autoRefreshSwitch'),
            refreshTimer: document.getElementById('refreshTimer'),
            instancesList: document.getElementById('instancesList'),
            connectionsList: document.getElementById('connectionsList'),
            instanceCount: document.getElementById('instanceCount'),
            connectionCount: document.getElementById('connectionCount'),
            loadingOverlay: document.getElementById('loadingOverlay')
        };
    },

    initializeComponents() {
        console.log('Initializing Bootstrap components...');
        if (typeof bootstrap === 'undefined') {
            throw new Error('Bootstrap is not loaded. Please check your dependencies.');
        }

        const instanceDetailsModal = document.getElementById('instanceDetailsModal');
        const instancePortMappingsModal = document.getElementById('instancePortMappingsModal');
        const customPortModal = document.getElementById('customPortModal');
        const preferencesModal = document.getElementById('preferencesModal');

        if (instanceDetailsModal) {
            this.modals.instanceDetails = new bootstrap.Modal(instanceDetailsModal);
        } else {
            console.warn('Instance details modal element not found');
        }

        if (instancePortMappingsModal) {
            this.modals.instancePortMappings = new bootstrap.Modal(instancePortMappingsModal);
        } else {
            console.warn('Instance preferences modal element not found');
        }

        if (customPortModal) {
            this.modals.customPort = new bootstrap.Modal(customPortModal);
        } else {
            console.warn('Custom port modal element not found');
        }

        const modeSelect = document.getElementById('modeSelect');
        if (modeSelect) {
            modeSelect.onchange = () => this.handleModeChange();
        } else {
            console.warn('Mode select element not found');
        }

        if (preferencesModal) {
            this.modals.preferences = new bootstrap.Modal(preferencesModal);
        } else {
            console.warn('Preferences modal element not found');
        }

        const preferencesBtn = document.getElementById('preferencesBtn');
        if (preferencesBtn) {
            preferencesBtn.onclick = () => this.showPreferences();
        } else {
            console.warn('Preferences button not found');
        }

        const themeToggleBtn = document.getElementById('themeToggle');
        if (themeToggleBtn) {
            themeToggleBtn.onclick = () => this.themeToggle();
        } else {
            console.warn('Theme toggle button not found');
        }

        const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltips.forEach(tooltip => {
            try {
                new bootstrap.Tooltip(tooltip);
            } catch (error) {
                console.warn('Failed to initialize tooltip:', error);
            }
        });

        const startPortForwardingBtn = document.getElementById('startPortForwardingBtn');
        if (startPortForwardingBtn) {
            startPortForwardingBtn.onclick = () => this.startCustomPortForwarding();
        }

        const savePreferencesBtn = document.getElementById('savePreferencesBtn');
        if (savePreferencesBtn) {
            savePreferencesBtn.onclick = () => this.savePreferences();
        } else {
            console.warn('Save preferences button not found');
        }

        const instancePortMappingsSaveBtn = document.getElementById('instancePortMappingsSaveBtn');
        if (instancePortMappingsSaveBtn) {
            instancePortMappingsSaveBtn.onclick = () => this.saveInstancePortMappings();
        }

        this.loadPreferences();
    },

    async loadProfilesAndRegions() {
        console.log('[Profile Loading] Starting to load profiles and regions...');
        try {
            const profilesRes = await fetch('/api/profiles');
            console.log('[Profile Loading] Profile response:', profilesRes);

            if (!profilesRes.ok) {
                throw new Error(`Failed to load profiles: ${profilesRes.status}`);
            }
            const profiles = await profilesRes.json();
            console.log('[Profile Loading] Loaded profiles:', profiles);

            const regionsRes = await fetch('/api/regions');
            console.log('[Profile Loading] Region response:', regionsRes);

            if (!regionsRes.ok) {
                throw new Error(`Failed to load regions: ${regionsRes.status}`);
            }
            const regions = await regionsRes.json();
            console.log('[Profile Loading] Loaded regions:', regions);

            if (Array.isArray(profiles)) {
                this.updateSelect(this.elements.profileSelect, profiles);
            } else {
                console.error('[Profile Loading] Invalid profiles data:', profiles);
            }

            if (Array.isArray(regions)) {
                this.updateSelect(this.elements.regionSelect, regions, '');
            } else {
                console.error('[Profile Loading] Invalid regions data:', regions);
            }
        } catch (error) {
            console.error('[Profile Loading] Error loading profiles and regions:', error);
            this.showError('Failed to load profiles and regions: ' + error.message);
        }
    },

    async loadLastUsedProfileAndRegion() {
        const lastProfile = localStorage.getItem(this.localProfile);
        if (lastProfile) {
            this.currentProfile = lastProfile;
            this.elements.profileSelect.value = lastProfile;
        }

        const lastRegion = localStorage.getItem(this.localRegion);
        if (lastRegion) {
            this.currentRegion = lastRegion;
            this.elements.regionSelect.value = lastRegion;
        }
    },

    updateSelect(select, options, defaultOption = '') {
        if (!select || !options) return;
        select.innerHTML = `<option value="">Select ${select.id.replace('Select', '')}</option>`;
        options.forEach(option => {
            const opt = document.createElement('option');
            opt.value = option;
            opt.textContent = option;
            opt.selected = option === defaultOption;
            select.appendChild(opt);
        });
    },

    async scanSubscription() {
        const profile = this.elements.profileSelect.value;
        const region = this.elements.regionSelect.value;

        if (!profile || !region) {
            this.showError('Please select both profile and region');
            return;
        }

        try {
            this.showLoading();
            this.elements.connectBtn.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden pe-2">Loading...</span></div>';
            const response = await fetch('/api/connect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ profile, region })
            });

            if (!response.ok) throw new Error('Scan failed');

            const result = await response.json();
            if (result.status === 'success') {
                this.currentProfile = profile;
                this.currentRegion = region;
                this.awsAccountId = result.account_id;

                this.updateAwsAccountDisplay();

                localStorage.setItem('lastProfile', profile);
                localStorage.setItem('lastRegion', region);

                await this.loadInstances();
                this.showSuccess('Scanned successfully');
            } else {
                throw new Error(result.error || 'Scan failed');
            }
        } catch (error) {
            this.showError('Scan error: ' + error.message);
        } finally {
            this.hideLoading();
            this.elements.connectBtn.innerHTML = '<i class="bi bi-search"></i>';
        }
    },

    updateAwsAccountDisplay() {
        const accountContainer = document.getElementById('accountIdContainer');
        const accountId = document.getElementById('awsAccountId');

        if (this.awsAccountId) {
            accountId.textContent = this.awsAccountId;
            accountContainer.style.display = 'block';
        } else {
            accountContainer.style.display = 'none';
            accountId.textContent = '';
        }
    },

    async loadInstances() {
        try {
            const response = await fetch('/api/instances');
            if (!response.ok) throw new Error('Failed to load instances');

            this.instances = await response.json();
            this.renderInstances();
            this.updateCounters();
        } catch (error) {
            this.showError('Failed to load instances: ' + error.message);
        }
    },

    renderInstances() {
        this.elements.instancesList.innerHTML = '';

        this.instances.forEach(instance => {
            const card = this.createInstanceCard(instance);
            this.elements.instancesList.appendChild(card);
        });
    },

    createInstanceCard(instance) {
        const card = document.createElement('div');
        card.className = `col-md-12 ${instance.has_ssm ? '' : 'non-ssm'}`;

        const statusClass = instance.state === 'running' ? 'success' : 'danger';

        card.innerHTML = `
                <div class="card instance-card h-100">
                    <div class="card-header d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <div class="mt-2">
                                <ul class="list-unstyled">
                                    <li><b>${instance.name}</b></li>
                                    <li><small class="text-muted">${instance.id}</small></li>
                                    <li>
                                        <span class="badge bg-${statusClass} status-badge">${instance.state}</span>
                                        <span class="badge bg-warning status-badge">${instance.type}</span>
                                        <span class="badge bg-info status-badge">${instance.os}</span>
                                        ${instance.has_ssm ?
                                            '<span class="badge badge-fucsia status-badge ms-1">SSM</span>' :
                                            '<span class="badge bg-secondary status-badge ms-1">SSM not found</span>'}
                                    </li>
                                <ul>
                            </div>
                        </div>
                        <div>
                            ${this.createActionButtons(instance.id, instance.name)}
                        </div>
                    </div>
                </div>
        `;

        return card;
    },

    createActionButtons(instanceId, instanceName) {
        return `
            <div class="d-flex justify-content-between mt-3 gap-2">
                ${this.instances.find(i => i.id === instanceId).has_ssm ? `
                    <button class="btn btn-sm btn-warning" onclick="app.startShell('${instanceId}')">
                        <i class="bi bi-terminal" title="Shell"></i>
                    </button>
                    <button class="btn btn-sm btn-primary" onclick="app.startRDP('${instanceId}')">
                        <i class="bi bi-display" title="RDP"></i>
                    </button>
                    <button class="btn btn-sm btn-purple text-white" onclick="app.showCustomPortModal('${instanceId}')">
                        <i class="bi bi-arrow-left-right" title="Port Forwarding"></i>
                    </button>
                ` : ''}
                <button class="btn btn-sm btn-ottanio text-white" onclick="app.showInstanceDetails('${instanceId}')">
                    <i class="bi bi-info-circle" title="Instance Details"></i>
                </button>
                <button class="btn btn-sm btn-darkseagreen text-white" onclick="app.showInstancePortMappings('${instanceId}', '${instanceName}')">
                    <i class="bi bi-sliders2" title="Instance Preferences"></i>
                </button>
            </div>
        `;
    },

    updateCounters() {
        this.elements.instanceCount.textContent = `${this.instances.length} instances`;
        if (this.instances.length === 0) {
            this.elements.instanceCount.classList.add('bg-secondary');
            this.elements.instanceCount.classList.remove('bg-success');
        } else {
            this.elements.instanceCount.classList.add('bg-success');
            this.elements.instanceCount.classList.remove('bg-secondary');
        }
        this.elements.connectionCount.textContent = `${this.connections.length} active`;
        if (this.connections.length === 0) {
            this.elements.connectionCount.classList.add('bg-secondary');
            this.elements.connectionCount.classList.remove('bg-success');
        } else {
            this.elements.connectionCount.classList.add('bg-success');
            this.elements.connectionCount.classList.remove('bg-secondary');
        }
    },

    async startShell(instanceId) {
        try {
            this.showLoading();
            const response = await fetch(`/api/shell/${instanceId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    profile: this.currentProfile,
                    region: this.currentRegion,
                    name: this.getInstanceName(instanceId)
                })
            });

            if (!response.ok) throw new Error('Failed to start Shell session');

            const result = await response.json();

            if (result.status === 'active') {
                this.addConnection(result);
                this.showSuccess('Shell session started successfully');
            } else {
                throw new Error(result.error || 'Failed to start Shell session');
            }
        } catch (error) {
            this.showError('Shell connection error: ' + error.message);
        } finally {
            this.hideLoading();
        }
    },

    async startRDP(instanceId) {
        try {
            this.showLoading();
            const response = await fetch(`/api/rdp/${instanceId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    profile: this.currentProfile,
                    region: this.currentRegion,
                    name: this.getInstanceName(instanceId)
                })
            });

            if (!response.ok) throw new Error('Failed to start RDP session');

            const result = await response.json();

            if (result.status === 'active') {
                this.addConnection(result);
                this.showSuccess(`RDP session started on port ${result.local_port}`);
            } else {
                throw new Error(result.error || 'Failed to start RDP session');
            }
        } catch (error) {
            this.showError('RDP connection error: ' + error.message);
        } finally {
            this.hideLoading();
        }
    },

    showCustomPortModal(instanceId) {
        console.log(`Showing custom port modal for instance ${instanceId}`);
        this.selectedInstanceId = instanceId;
        this.modals.customPort.show();
    },

    async showInstanceDetails(instanceId) {
        console.log(`Showing instance details for ${instanceId}`);
        try {
            const response = await fetch(`/api/instance-details/${instanceId}`);
            if (!response.ok) throw new Error('Failed to fetch instance details');

            const details = await response.json();
            if (!details) throw new Error('No instance details found');

            const contentDiv = document.getElementById('instanceDetailsContent');
            contentDiv.innerHTML = `
                <div class="table-responsive">
                    <table class="table table-hover">
                        <tbody>
                            ${this.createDetailRow('Instance ID', details.id)}
                            ${this.createDetailRow('Name', details.name)}
                            ${this.createDetailRow('Platform', details.platform)}
                            ${this.createDetailRow('Public IPv4', details.public_ip)}
                            ${this.createDetailRow('Private IPv4', details.private_ip)}
                            ${this.createDetailRow('VPC ID', details.vpc_id)}
                            ${this.createDetailRow('Subnet ID', details.subnet_id)}
                            ${this.createDetailRow('IAM Role', details.iam_role)}
                            ${this.createDetailRow('AMI ID', details.ami_id)}
                            ${this.createDetailRow('SSH Key', details.key_name)}
                            ${this.createDetailRow('Security Groups', details.security_groups)}
                        </tbody>
                    </table>
                    <div class="text-muted small text-center mt-2">
                        Click on any value to copy to clipboard
                    </div>
                </div>
            `;

            contentDiv.querySelectorAll('.copy-value').forEach(element => {
                element.addEventListener('click', () => this.copyToClipboard(element.dataset.value));
            });

            this.modals.instanceDetails.show();
        } catch (error) {
            console.error('Error showing instance details:', error);
            this.showError('Failed to load instance details');
        }
    },

    createDetailRow(label, value) {
        return `
            <tr>
                <td class="fw-bold" style="width: 35%">${label}</td>
                <td>
                    <span class="copy-value" role="button" data-value="${value}"
                          style="cursor: pointer" title="Click to copy">
                        ${value}
                    </span>
                </td>
            </tr>
        `;
    },

    async showInstancePortMappings(instanceId, instanceName) {
      console.log(`Showing instance preferences for ${instanceId} (${instanceName})`);
      try {
        const details = [];
        const others = [];
        this.preferences.instances.forEach(i => {
          if (i.name === instanceName) {
            details.push(i);
          } else {
            i.ports.forEach(p => {
              others.push(p.local_port);
            });
          }
        });

        let mappingCount = -1
        const detailsHtml = details.map(d => {
          return d.ports.map(p => {
            let duplicate = false;
            if (others.includes(p.local_port)) {
              duplicate = true;
            }
            return this.createInstancePortMappingsRow(p.local_port, p.remote_host ? p.remote_host + ":" + p.remote_port : p.remote_port, ++mappingCount, duplicate);
          }).join('');
        }).join('');

        const contentDiv = document.getElementById('instancePortMappingsContent');
        contentDiv.innerHTML = `
          <input type="hidden" id="instanceId" value="${instanceId}">
          <input type="hidden" id="instanceName" value="${instanceName}">
          <div class="container text-center port-mappings">
            <div class="row mb-2 fw-bold border-bottom">
              <div class="col">
                Local Port
              </div>
              <div class="col">
                Remote [Host:]Port
              </div>
            </div>
            ${detailsHtml}
          </div>
          <div class="container text-center">
            <div class="row mb-2">
              <div class="col">
                <div class="col input-group">
                  <input id="localPort_New" type="text" class="form-control" placeholder="50000" aria-label="Local Port">
                  <input id="remoteHostPort_New" type="text" class="form-control" placeholder="80 or <ip address>:80" aria-label="Remote [Host:]Port">
                  <button class="btn btn-outline-primary" type="button" id="mappingAddButton"><i class="bi bi-plus-square"></i></button>
                </div>
              </div>
            </div>
          </div>
        `;

        contentDiv.querySelectorAll('.port-mapping').forEach((row, idx)=> {
          const mappingDeleteButton = document.getElementById(`mappingDelete_${idx}`);
          mappingDeleteButton.addEventListener('click', () => {
            this.deleteInstancePortMappingsRow(idx);
          });
        });

        const addButton = document.getElementById('mappingAddButton');
        addButton.addEventListener('click', () => {
          this.addInstancePortMappingsRow()
        });

        this.modals.instancePortMappings.show();
      } catch (error) {
        console.error('Error showing instance preferences:', error);
        this.showError('Failed to load instance preferences');
      }
    },

    async saveInstancePortMappings() {
      const instanceId = document.getElementById('instanceId').value;
      const instanceName = document.getElementById('instanceName').value;
      const allPortMappings = document.querySelectorAll('.port-mapping');
      const portMappings = Array.from(allPortMappings).map(row => {
        const localPort = row.querySelector('input[id^="localPort_"]').value;
        const remoteHostPort = row.querySelector('input[id^="remoteHostPort_"]').value;
        const portMapping = {
          local_port: localPort,
          remote_port: remoteHostPort.includes(':') ? remoteHostPort.split(':')[1] : remoteHostPort
        };
        const remote_host = remoteHostPort.includes(':') ? remoteHostPort.split(':')[0] : undefined;
        if (remote_host) {
          portMapping.remote_host = remote_host;
        }
        return portMapping;
      });
      const newPreferences = {
        name: instanceName,
        ports: portMappings
      }
      console.log('Saving instance preferences:', newPreferences);
      const response = await fetch('/api/preferences/' + instanceName, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newPreferences)
      });
      if (!response.ok) throw new Error('Failed to save instance preferences');

      await this.loadPreferences();

      if (this.modals.instancePortMappings) {
        this.modals.instancePortMappings.hide();
      }
      this.showSuccess('Instance preferences saved successfully');
    },

    createInstancePortMappingsRow(localPort, remoteHostPort, mappingCount, duplicate) {
      let duplicationNotice = '';
      if (duplicate) {
        duplicationNotice = `
          <div class="text-muted text-small">
            Duplicate local port assignment detected for ${localPort}.
          </div>
        `;
      }
      return `
        <div class="row mb-2" id="portMapping_${mappingCount}">
            <div class="col">
                <div class="col input-group port-mapping">
                    <input id="localPort_${mappingCount}" type="text" class="form-control" placeholder="Local Port" aria-label="Local Port" value="${localPort}">
                    <input id="remoteHostPort_${mappingCount}" type="text" class="form-control" placeholder="Remote [Host:]Port" aria-label="Remote [Host:]Port" value="${remoteHostPort}">
                    <button class="btn btn-outline-danger" type="button" id="mappingDelete_${mappingCount}"><i class="bi bi-trash"></i></button>
                </div>
                ${duplicationNotice}
            </div>
        </div>
      `;
    },

    deleteInstancePortMappingsRow(mappingCount) {
      const portMapping = document.getElementById(`portMapping_${mappingCount}`);
      if (portMapping) {
        portMapping.remove();
      }
    },

    addInstancePortMappingsRow() {
      const allPortMappings = document.querySelectorAll('.port-mapping');
      mappingCount = allPortMappings.length + 1;

      const localPortInput = document.getElementById('localPort_New');
      const remoteHostPortInput = document.getElementById('remoteHostPort_New');
      if (localPortInput.value === '' || remoteHostPortInput.value === '') {
        this.showError('Please fill in both fields');
        return;
      }

      const newRow = this.createInstancePortMappingsRow(
        localPortInput.value, remoteHostPortInput.value, mappingCount
      );
      const portMappings = document.querySelector('.port-mappings');
      portMappings.insertAdjacentHTML('beforeend', newRow);

      const newDeleteButton = document.getElementById(`mappingDelete_${mappingCount}`);
      newDeleteButton.addEventListener('click', () => {
        this.deleteInstancePortMappingsRow(mappingCount);
      });

      localPortInput.value = '';
      remoteHostPortInput.value = '';
    },

    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showSuccess('Copied to clipboard');
        } catch (error) {
            console.error('Failed to copy:', error);
            this.showError('Failed to copy to clipboard');
        }
    },

    addConnection(connection) {
        this.connections.push(connection);
        this.checkConnections();
    },

    async terminateConnection(connectionId) {
        try {
            this.showLoading();
            const response = await fetch(`/api/terminate-connection/${connectionId}`, {
                method: 'POST'
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to terminate connection');
            }

            this.connections = this.connections.filter(c => c.id !== connectionId);
            this.renderConnections();
            this.updateCounters();
            this.checkConnections();
            this.showSuccess('Connection terminated successfully');
        } catch (error) {
            this.showError('Failed to terminate connection: ' + error.message);
        } finally {
            this.hideLoading();
        }
    },

    getInstanceName(instanceId) {
        const instance = this.instances.find(i => i.id === instanceId);
        return instance ? instance.name : instanceId;
    },
};

app.refreshData = async function() {
  try {
    this.showLoading();

    await this.loadProfilesAndRegions();
    await this.loadLastUsedProfileAndRegion();

    const response = await fetch('/api/refresh', {
      method: 'GET'
    });

    if (!response.ok) throw new Error('Refresh failed');

    const result = await response.json();
    if (result.status === 'success') {
      this.instances = result.instances;
      this.renderInstances();
      this.updateCounters();
      this.showSuccess('Data refreshed successfully');
    }
  } catch (error) {
    this.showError('Failed to refresh data: ' + error.message);
    this.toggleAutoRefresh(false);
  } finally {
    this.hideLoading();
  }
};

app.toggleAutoRefresh = function(enabled) {
  if (enabled?.target) {
    enabled = enabled.target.checked;
  }

  console.log('Toggle auto-refresh:', enabled);
  if (enabled) {
    this.startAutoRefresh();
  } else {
    this.stopAutoRefresh();
  }
};

app.startAutoRefresh = function() {
  console.log('Starting auto-refresh');
  this.refreshCountdown = 30;
  this.updateRefreshTimer();

  if (this.refreshInterval) {
    clearInterval(this.refreshInterval);
  }

  this.refreshInterval = setInterval(() => {
    this.refreshCountdown--;
    this.updateRefreshTimer();

    if (this.refreshCountdown <= 0) {
      this.refreshData();
      this.refreshCountdown = 30;
    }
  }, 1000);
};

app.stopAutoRefresh = function() {
  console.log('Stopping auto-refresh');
  if (this.refreshInterval) {
    clearInterval(this.refreshInterval);
    this.refreshInterval = null;
  }

  this.refreshCountdown = 0;
  this.elements.refreshTimer.textContent = '';
  this.elements.autoRefreshSwitch.checked = false;
};

app.setupEventListeners = function() {
  console.log('Setting up event listeners...');
  this.elements.connectBtn.onclick = () => this.scanSubscription();
  this.elements.refreshBtn.onclick = () => this.refreshData();

  this.elements.autoRefreshSwitch.onchange = (e) => {
    this.toggleAutoRefresh(e.target.checked);
  };
};

app.updateRefreshTimer = function() {
  if (this.elements.autoRefreshSwitch.checked && this.refreshCountdown > 0) {
    this.elements.refreshTimer.textContent = `(${this.refreshCountdown}s)`;
  } else {
    this.elements.refreshTimer.textContent = '';
  }
};

app.showPreferences = async function() {
  console.log('Showing preferences dialog');
  try {
    const preferencesRes = await fetch('/api/preferences');
    if (!preferencesRes.ok) throw new Error('Failed to load preferences');
    const prefs = await preferencesRes.json();

    const regionsAllRes = await fetch('/api/regions/all');
    if (!regionsAllRes.ok) throw new Error('Failed to load all regions');
    const regionsAll = await regionsAllRes.json();

    if (Array.isArray(regionsAll)) {
      const select = this.elements.regionsSelect;
      if (!select) return;
      select.innerHTML = '';

      regionsAll.forEach(option => {
        const opt = document.createElement('option');
        opt.value = option;
        opt.textContent = option;
        opt.selected = prefs.regions.includes(option);
        select.appendChild(opt);
      });
    } else {
      console.error('Invalid regions data:', regionsAll);
    }

    document.getElementById('startPort').value = prefs.port_range.start;
    document.getElementById('endPort').value = prefs.port_range.end;
    document.getElementById('logLevel').value = prefs.logging.level;

    if (this.modals.preferences) {
      this.modals.preferences.show();
    } else {
      console.error('Preferences modal not initialized');
    }
  } catch (error) {
    console.error('Error loading preferences:', error);
    this.showError('Failed to load current preferences');
  }
};

app.savePreferences = async function() {
  console.log('Saving preferences');
  try {
    const startPort = parseInt(document.getElementById('startPort').value);
    const endPort = parseInt(document.getElementById('endPort').value);
    const logLevel = document.getElementById('logLevel').value;
    const selectedRegions = this.elements.regionsSelect.querySelectorAll('option:checked');
    const newRegions = Array.from(selectedRegions).map(r => r.value);

    if (startPort >= endPort) {
      this.showError('Start port must be less than end port');
      return;
    }

    if (startPort < 1024 || endPort > 65535) {
      this.showError('Ports must be between 1024 and 65535');
      return;
    }

    const newPreferences = {
      port_range: {
        start: startPort,
        end: endPort
      },
      logging: {
        level: logLevel
      },
      regions: newRegions
    };

    const response = await fetch('/api/preferences', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newPreferences)
    });
    if (!response.ok) throw new Error('Failed to save preferences');

    await this.loadPreferences();
    await this.loadProfilesAndRegions();
    await this.loadLastUsedProfileAndRegion();

    if (this.modals.preferences) {
      this.modals.preferences.hide();
    }
    this.showSuccess('Preferences saved successfully');
  } catch (error) {
    console.error('Error saving preferences:', error);
    this.showError('Failed to save preferences');
  }
};

app.loadPreferences = async function() {
  console.log('Loading initial preferences');
  try {
    const response = await fetch('/api/preferences');
    if (!response.ok) throw new Error('Failed to load preferences');

    this.preferences = await response.json();
  } catch (error) {
    console.error('Error loading initial preferences:', error);
  }
};

app.handleModeChange = function() {
  const remotePortContainer = document.getElementById('remotePortContainer');
  const otherHostContainer = document.getElementById('otherHostContainer');
  const modeSelect = document.getElementById('modeSelect');

  if (modeSelect.value === 'local') {
    remotePortContainer.style.display = 'block';
    otherHostContainer.style.display = 'none';
  } else {
    remotePortContainer.style.display = 'none';
    otherHostContainer.style.display = 'block';
  }
};

app.startCustomPortForwarding = async function() {
  const mode = document.getElementById('modeSelect').value;
  const instanceId = this.selectedInstanceId;

  if (mode === 'local') {
    const remotePort = document.getElementById('remotePort').value;
    if (!remotePort || !instanceId) {
      this.showError('Please specify a remote port');
      return;
    }
  } else {
    const remoteHost = document.getElementById('remoteHost').value;
    const remotePort = document.getElementById('otherRemotePort').value;
    if (!remoteHost || !remotePort || !instanceId) {
      this.showError('Please specify both remote host and port');
      return;
    }
  }

  this.showLoading();

  try {
    let requestData = {
      profile: this.currentProfile,
      region: this.currentRegion,
      name: this.getInstanceName(instanceId),
      mode: mode
    };

    if (mode === 'local') {
      requestData.remote_port = document.getElementById('remotePort').value;
    } else {
      requestData.remote_host = document.getElementById('remoteHost').value;
      requestData.remote_port = document.getElementById('otherRemotePort').value;
    }

    const response = await fetch(`/api/custom-port/${instanceId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestData)
    });

    if (!response.ok) throw new Error('Failed to start port forwarding');
    const result = await response.json();

    if (result.status === 'active') {
      this.addConnection(result);
      this.modals.customPort.hide();
      this.showSuccess('Port fowarding started successfully');
    }
  } catch (error) {
    this.showError('Port forwarding error: ' + error.message);
  } finally {
    this.hideLoading();
  }
};

app.timeAgo = function(timestamp) {
  const now = Date.now();
  const seconds = Math.floor((now - timestamp * 1000) / 1000);

  const intervals = {
    year: 31536000,
    month: 2592000,
    day: 86400,
    hour: 3600,
    minute: 60,
    second: 1,
  };

  for (const unit in intervals) {
    const interval = intervals[unit];
    const count = Math.floor(seconds / interval);

    if (count >= 1) {
      const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' });
      return rtf.format(-count, unit);
    }
  }
  return 'just now';
};

app.renderConnections = function() {
  const container = this.elements.connectionsList;
  container.innerHTML = '';

  if (this.connections.length === 0) {
    container.innerHTML = `
      <div class="text-center text-muted p-4">
        <i class="bi bi-diagram-2 fs-2"></i>
        <p class="mt-2">No active connections</p>
      </div>
    `;
    return;
  }

  this.connections.forEach(conn => {
    const element = document.createElement('div');
    element.className = 'connection-item border border-secondary';

    const timestamp = new Date(conn.timestamp * 1000).toLocaleString();
    const timeago = this.timeAgo(conn.timestamp);

    let connectionInfo = '';
    if (conn.type === 'RDP' || conn.type === 'Custom Port' || conn.type === 'Remote Host Port') {
      connectionInfo = `
        <div class="text-muted small">
          <p class="m-0 p-0">Local Port: ${conn.local_port}</p>
          ${conn.remote_port ? `<p class="m-0 p-0">Remote Port: ${conn.remote_port}` : ''}
          ${conn.remote_host ? `, Host: ${conn.remote_host}</p>` : '</p>'}
        </div>
      `;
    }

    element.innerHTML = `
      <div class="d-flex justify-content-between align-items-start">
        <div>
          <div class="d-flex align-items-center gap-2">
            <button type="button" class="btn btn-sm ${this.getConnectionTypeColor(conn.type)}"
             style="--bs-btn-padding-y: .15rem; --bs-btn-padding-x: .45rem; --bs-btn-font-size: .70rem;"
             ${this.getConnectionTypeAction(conn)}>
                ${conn.type}
            </button>
          </div>
          <div title="${conn.instance.id}">
            <b>${conn.name !== '' ? conn.name : conn.instance.id}</b>
            ${connectionInfo}
          </div>
          <p class="text-muted small mt-2 mb-1" title="${timestamp}">Started ${timeago}</p>
          <div class="d-flex align-items-center gap-2">
            <span class="badge" style="background-color: #fd9843;">${conn.region}</span>
            <span class="badge" style="background-color: #e35d6a;">${conn.profile}</span>
          </div>
        </div>
        <button class="btn btn-sm btn-outline-danger" onclick="app.terminateConnection('${conn.connection_id}')">
          <i class="bi bi-x-lg"></i>
        </button>
      </div>
    `;

    container.appendChild(element);
  });
};

app.getConnectionTypeAction = function(conn) {
  const actions = {
    'RDP': "onclick=\"app.openRdp('" + conn.local_port + "')\""
  };
  return actions[conn.type] || '';
};

app.getConnectionTypeColor = function(type) {
  const colors = {
    'Shell': 'text-bg-warning',
    'RDP': 'text-bg-primary',
    'Custom Port': 'btn-purple',
    'Remote Host Port': 'btn-purple'
  };
  return colors[type] || 'text-bg-secondary';
};

app.openRdp = async function(local_port) {
  try {
    this.showLoading();
    const response = await fetch(`/api/rdp/${local_port}`, {
      method: 'GET'
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to open RDP client');
    }

    this.showSuccess('RDP client opened successfully');
  } catch (error) {
    this.showError('Failed to open RDP client: ' + error.message);
  } finally {
    this.hideLoading();
  }
};

app.startConnectionMonitoring = function() {
  console.log('Starting connection monitoring');
  if (this.monitoringInterval) {
    clearInterval(this.monitoringInterval);
  }
  this.monitoringInterval = setInterval(() => this.checkConnections(), 2500);
};

app.checkConnections = async function() {
  try {
    const response = await fetch('/api/active-connections');
    if (!response.ok) throw new Error('Failed to check connections');
    const activeConnections = await response.json();

    if (this.connections.length === 0) {
      this.connections = activeConnections;
      this.renderConnections();
      this.updateCounters();
      return;
    }

    const activeIds = new Set(activeConnections.map(c => c.connection_id));

    this.connections.forEach(conn => {
      if (!activeIds.has(conn.connection_id)) {
        this.showToast(`Connection to ${this.getInstanceName(conn.instance.id)} was terminated`, 'warning');
      }
    });

    this.connections = activeConnections;
    this.renderConnections();
    this.updateCounters();
  } catch (error) {
    console.error('Error checking connections:', error);
  }
};

app.showToast = function(message, type = 'info') {
  const toastContainer = document.querySelector('.toast-container');
  const toast = document.createElement('div');
  toast.className = `toast align-items-center border-0 bg-${type} text-white`;
  toast.setAttribute('role', 'alert');
  toast.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">${message}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
    </div>
  `;
  toastContainer.appendChild(toast);
  const bsToast = new bootstrap.Toast(toast);
  bsToast.show();
  toast.addEventListener('hidden.bs.toast', () => toast.remove());
};

app.showSuccess = function(message) {
  this.showToast(message, 'success');
};

app.showError = function(message) {
  this.showToast(message, 'danger');
};

app.showLoading = function() {
  if (this.elements.loadingOverlay) {
    const openModals = document.querySelectorAll('.modal.show');
    openModals.forEach(modal => {
      modal.classList.add('modal-loading');
    });

    this.elements.loadingOverlay.classList.remove('d-none');
  }
};

app.hideLoading = function() {
  if (this.elements.loadingOverlay) {
    const openModals = document.querySelectorAll('.modal.show');
    openModals.forEach(modal => {
      modal.classList.remove('modal-loading');
    });

    this.elements.loadingOverlay.classList.add('d-none');
  }
};

app.themeToggle = function() {
  const newTheme = app.currentTheme() === 'light' ? 'dark' : 'light';
  app.setTheme(newTheme);
};

app.setTheme = function(theme) {
  document.documentElement.setAttribute('data-bs-theme', theme);
  localStorage.setItem(this.localTheme, theme);
};

app.currentTheme = function() {
  return document.documentElement.getAttribute('data-bs-theme');
};

app.loadTheme = function() {
  const theme = localStorage.getItem(this.localTheme);
  if (theme) {
    this.setTheme(theme);
  }
};


// Initialize app when document is ready
document.addEventListener('DOMContentLoaded', () => app.init());
