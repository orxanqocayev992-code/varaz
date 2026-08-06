// Statistika reqemlerinin 0-dan yuxari sayilaraq animasiyasi
document.querySelectorAll('.stat-counter').forEach(function (el) {
  var target = parseInt(el.dataset.target, 10) || 0;
  var duration = 1100;
  var startTime = null;
  function step(ts) {
    if (!startTime) startTime = ts;
    var progress = Math.min((ts - startTime) / duration, 1);
    var eased = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.floor(eased * target);
    if (progress < 1) requestAnimationFrame(step);
    else el.textContent = target;
  }
  requestAnimationFrame(step);
});

// Flash mesajlarini bir muddetden sonra gizlet
document.querySelectorAll('.flash').forEach(function (el) {
  setTimeout(function () { el.style.transition = 'opacity .4s'; el.style.opacity = '0'; }, 3200);
  setTimeout(function () { el.remove(); }, 3700);
});

// Iki-tereфli (dual) range slider - qiymet ve il filtrleri ucun
function wireDualSlider(minInputId, maxInputId, minRangeId, maxRangeId, fillId, boundMin, boundMax) {
  var minInput = document.getElementById(minInputId);
  var maxInput = document.getElementById(maxInputId);
  var minRange = document.getElementById(minRangeId);
  var maxRange = document.getElementById(maxRangeId);
  var fill = document.getElementById(fillId);
  if (!minInput || !maxInput || !minRange || !maxRange || !fill) return;

  function update() {
    var minV = parseFloat(minRange.value);
    var maxV = parseFloat(maxRange.value);
    if (minV > maxV) { var t = minV; minV = maxV; maxV = t; }
    var pct1 = ((minV - boundMin) / (boundMax - boundMin)) * 100;
    var pct2 = ((maxV - boundMin) / (boundMax - boundMin)) * 100;
    fill.style.left = pct1 + '%';
    fill.style.width = (pct2 - pct1) + '%';
  }

  minRange.addEventListener('input', function () {
    if (parseFloat(minRange.value) > parseFloat(maxRange.value)) minRange.value = maxRange.value;
    minInput.value = minRange.value;
    update();
  });
  maxRange.addEventListener('input', function () {
    if (parseFloat(maxRange.value) < parseFloat(minRange.value)) maxRange.value = minRange.value;
    maxInput.value = maxRange.value;
    update();
  });
  minInput.addEventListener('change', function () {
    var v = Math.max(boundMin, Math.min(parseFloat(minInput.value) || boundMin, boundMax));
    minRange.value = v; minInput.value = v;
    update();
  });
  maxInput.addEventListener('change', function () {
    var v = Math.max(boundMin, Math.min(parseFloat(maxInput.value) || boundMax, boundMax));
    maxRange.value = v; maxInput.value = v;
    update();
  });
  update();
}

// ================== Nəqliyyat elanı - Turbo.az meqli ardıcıl addımlar ==================
var TURBO_CHAIN = ['make', 'model', 'year', 'body_type', 'fuel_type', 'drivetrain', 'transmission',
                    'modification', 'color', 'market', 'mileage'];

function wireTurboWizard() {
  var container = document.querySelector('.turbo-wizard');
  if (!container) return;
  var steps = {};
  container.querySelectorAll('.turbo-step').forEach(function (el) {
    steps[el.dataset.turboStep] = el;
  });

  function isStepComplete(key) {
    var el = steps[key];
    if (!el) return true;
    var radios = el.querySelectorAll('input[type=radio]');
    if (radios.length) {
      return Array.prototype.some.call(radios, function (r) { return r.checked; });
    }
    if (key === 'mileage') {
      var num = el.querySelector('input[type=number]');
      return !!(num && num.value.trim() !== '');
    }
    var select = el.querySelector('select');
    if (select) return !!select.value;
    var input = el.querySelector('input[type=text], input[type=number]');
    if (input) return input.value.trim() !== '';
    return true;
  }

  function setEnabled(el, enabled) {
    el.querySelectorAll('input, select, button').forEach(function (i) { i.disabled = !enabled; });
  }

  function unlock(key) {
    var el = steps[key];
    if (!el || !el.classList.contains('locked')) return;
    el.classList.remove('locked');
    el.classList.add('just-unlocked');
    setEnabled(el, true);
    setTimeout(function () { el.classList.remove('just-unlocked'); }, 400);
  }

  function refresh() {
    for (var i = 0; i < TURBO_CHAIN.length; i++) {
      var key = TURBO_CHAIN[i];
      var complete = isStepComplete(key);
      steps[key] && steps[key].classList.toggle('done', complete);
      if (complete) {
        var next = TURBO_CHAIN[i + 1];
        if (next) unlock(next);
      } else {
        break;
      }
    }
    if (isStepComplete('mileage')) {
      ['equipment', 'condition', 'vin'].forEach(unlock);
    }
  }

  container.addEventListener('change', refresh);
  container.addEventListener('input', refresh);

  // Chip / swatch vizual sechim (radio qruplarini vizual bildirir)
  container.querySelectorAll('.turbo-chip, .turbo-swatch').forEach(function (label) {
    label.addEventListener('click', function () {
      var input = label.querySelector('input');
      if (!input || input.disabled) return;
      var name = input.name;
      container.querySelectorAll('input[name="' + name + '"]').forEach(function (inp) {
        var lbl = inp.closest('.turbo-chip, .turbo-swatch');
        if (lbl) lbl.classList.remove('selected');
      });
      input.checked = true;
      label.classList.add('selected');
      refresh();
    });
  });

  // Veziyyet - Beli/Xeyr duymeleri
  container.querySelectorAll('.turbo-yesno').forEach(function (group) {
    var name = group.dataset.name;
    var hidden = container.querySelector('input[type=hidden][name="' + name + '"]');
    group.querySelectorAll('button').forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (btn.disabled) return;
        group.querySelectorAll('button').forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        if (hidden) hidden.value = btn.dataset.val;
      });
    });
  });

  // Elave (custom) techizat elave etme
  var addBtn = document.getElementById('addEquipmentBtn');
  var customInput = document.getElementById('customEquipmentInput');
  var customList = document.getElementById('customEquipmentList');
  if (addBtn && customInput && customList) {
    addBtn.addEventListener('click', function () {
      if (addBtn.disabled) return;
      var val = customInput.value.trim();
      if (!val) return;
      var label = document.createElement('label');
      label.className = 'turbo-check-item';
      var input = document.createElement('input');
      input.type = 'checkbox'; input.name = 'equipment'; input.value = val; input.checked = true;
      label.appendChild(input);
      label.appendChild(document.createTextNode(val));
      customList.appendChild(label);
      customInput.value = '';
    });
  }

  // VIN kod canli yoxlama
  var vinInput = document.getElementById('vinInput');
  var vinHint = document.getElementById('vinHint');
  if (vinInput && vinHint) {
    vinInput.addEventListener('input', function () {
      var v = vinInput.value.toUpperCase().replace(/\s/g, '');
      vinInput.value = v;
      vinInput.classList.remove('vin-valid', 'vin-invalid');
      if (!v) {
        vinHint.textContent = 'VIN kod avtomobilin unikal identifikasiya nömrəsidir (17 simvol).';
        vinHint.style.color = '';
        return;
      }
      var valid = v.length === 17 && /^[A-HJ-NPR-Z0-9]+$/.test(v);
      if (valid) {
        vinInput.classList.add('vin-valid');
        vinHint.textContent = '✓ VIN kod düzgün formatdadır.';
        vinHint.style.color = '#2e8b57';
      } else {
        vinInput.classList.add('vin-invalid');
        vinHint.textContent = '⚠ VIN kod 17 simvoldan ibarət olmalı və I, O, Q hərflərini ehtiva etməməlidir. (' + v.length + '/17)';
        vinHint.style.color = 'var(--tred, #E4483A)';
      }
    });
  }

  refresh();
}

// Sherik sahelerin (Qiymet/Seher/Elaqe/Basliq/Tesvir) Neqliyyat axininda sona kocurulmesi
function repositionSharedFields(type) {
  var sharedBlock = document.getElementById('sharedFieldsBlock');
  var sharedAnchor = document.getElementById('sharedFieldsAnchor');
  var vehicleFieldsEl = document.getElementById('vehicleFields');
  if (!sharedBlock || !sharedAnchor || !vehicleFieldsEl) return;
  if (type === 'neqliyyat') {
    vehicleFieldsEl.appendChild(sharedBlock);
  } else if (sharedAnchor.parentNode) {
    sharedAnchor.parentNode.insertBefore(sharedBlock, sharedAnchor);
  }
}

// Sekil yukleme: surukle-burax, sıralama, esas sekil secimi
function wireImageUploader(inputSelector, previewId, dropzoneId) {
  var input = document.querySelector(inputSelector);
  var preview = document.getElementById(previewId);
  var dropzone = document.getElementById(dropzoneId);
  var countHint = document.getElementById('imageCountHint');
  if (!input || !preview) return;
  var fileList = [];

  function syncInput() {
    var dt = new DataTransfer();
    fileList.forEach(function (f) { dt.items.add(f); });
    input.files = dt.files;
    if (countHint) {
      var n = fileList.length;
      countHint.textContent = n + ' şəkil seçilib' + (n > 0 ? ' (birincisi əsas şəkildir, sürükləyərək sırasını dəyişə bilərsiniz).' : '.');
      countHint.style.color = (n > 0 && n < 3) ? 'var(--danger)' : '';
    }
  }

  function makePrimary(idx) {
    var f = fileList.splice(idx, 1)[0];
    fileList.unshift(f);
    syncInput(); renderPreview();
  }
  function removeFile(idx) {
    fileList.splice(idx, 1);
    syncInput(); renderPreview();
  }

  function renderPreview() {
    preview.innerHTML = '';
    fileList.forEach(function (file, idx) {
      var item = document.createElement('div');
      item.className = 'img-preview-item' + (idx === 0 ? ' primary' : '');
      item.draggable = true;
      var img = document.createElement('img');
      var reader = new FileReader();
      reader.onload = (function (imgEl) { return function (e) { imgEl.src = e.target.result; }; })(img);
      reader.readAsDataURL(file);
      item.appendChild(img);
      if (idx === 0) {
        var badge = document.createElement('span');
        badge.className = 'primary-badge'; badge.textContent = 'Əsas';
        item.appendChild(badge);
      } else {
        var setBtn = document.createElement('button');
        setBtn.type = 'button'; setBtn.className = 'set-primary-btn'; setBtn.textContent = 'Əsas et';
        setBtn.addEventListener('click', function (e) { e.stopPropagation(); makePrimary(idx); });
        item.appendChild(setBtn);
      }
      var rmBtn = document.createElement('button');
      rmBtn.type = 'button'; rmBtn.className = 'remove-btn'; rmBtn.textContent = '×';
      rmBtn.addEventListener('click', function (e) { e.stopPropagation(); removeFile(idx); });
      item.appendChild(rmBtn);

      item.addEventListener('dragstart', function (e) { e.dataTransfer.setData('text/plain', String(idx)); });
      item.addEventListener('dragover', function (e) { e.preventDefault(); });
      item.addEventListener('drop', function (e) {
        e.preventDefault();
        var fromIdx = parseInt(e.dataTransfer.getData('text/plain'), 10);
        if (isNaN(fromIdx) || fromIdx === idx) return;
        var moved = fileList.splice(fromIdx, 1)[0];
        fileList.splice(idx, 0, moved);
        syncInput(); renderPreview();
      });
      preview.appendChild(item);
    });
  }

  function addFiles(newFiles) {
    Array.prototype.forEach.call(newFiles, function (f) {
      if (fileList.length < 21 && f.type && f.type.indexOf('image/') === 0) fileList.push(f);
    });
    syncInput(); renderPreview();
  }

  input.addEventListener('change', function () { addFiles(input.files); });
  if (dropzone) {
    dropzone.addEventListener('click', function (e) { if (e.target === dropzone || e.target.tagName !== 'INPUT') input.click(); });
    dropzone.addEventListener('dragover', function (e) { e.preventDefault(); dropzone.classList.add('dragover'); });
    dropzone.addEventListener('dragleave', function () { dropzone.classList.remove('dragover'); });
    dropzone.addEventListener('drop', function (e) {
      e.preventDefault(); dropzone.classList.remove('dragover');
      addFiles(e.dataTransfer.files);
    });
  }
}

// Mobil hamburger menyu
var navToggle = document.getElementById('navToggle');
var siteHeader = document.querySelector('.site-header');
if (navToggle && siteHeader) {
  navToggle.addEventListener('click', function () {
    siteHeader.classList.toggle('nav-open');
  });
  document.querySelectorAll('#mainNav a, #headerActions a').forEach(function (link) {
    link.addEventListener('click', function () { siteHeader.classList.remove('nav-open'); });
  });
}

// Sekil onizlemesi (yeni/redakte elan formalarinda)
function wireImagePreview(inputEl, previewEl) {
  if (!inputEl || !previewEl) return;
  inputEl.addEventListener('change', function () {
    previewEl.innerHTML = '';
    var files = Array.prototype.slice.call(inputEl.files).slice(0, 12);
    files.forEach(function (file) {
      if (!file.type || file.type.indexOf('image/') !== 0) return;
      var reader = new FileReader();
      reader.onload = function (e) {
        var img = document.createElement('img');
        img.src = e.target.result;
        previewEl.appendChild(img);
      };
      reader.readAsDataURL(file);
    });
  });
}
// (sekil onizlemesi hər sehifenin oz extra_scripts blokunda cagirilir)

// Xeritede yerlesme secimi (yeni/redakte elan formalarinda)
function wireLocationPicker(mapElId, latInputId, lngInputId, initialLat, initialLng) {
  var mapEl = document.getElementById(mapElId);
  var latInput = document.getElementById(latInputId);
  var lngInput = document.getElementById(lngInputId);
  if (!mapEl || typeof L === 'undefined') return;
  var startLat = initialLat || 40.4093;
  var startLng = initialLng || 49.8671;
  var map = L.map(mapElId).setView([startLat, startLng], initialLat ? 14 : 11);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap', maxZoom: 19
  }).addTo(map);
  var marker = null;
  function setMarker(lat, lng) {
    if (marker) { marker.setLatLng([lat, lng]); }
    else { marker = L.marker([lat, lng], { draggable: true }).addTo(map);
      marker.on('dragend', function () {
        var pos = marker.getLatLng();
        if (latInput) latInput.value = pos.lat.toFixed(6);
        if (lngInput) lngInput.value = pos.lng.toFixed(6);
      });
    }
    if (latInput) latInput.value = lat.toFixed(6);
    if (lngInput) lngInput.value = lng.toFixed(6);
  }
  if (initialLat && initialLng) setMarker(initialLat, initialLng);
  map.on('click', function (e) { setMarker(e.latlng.lat, e.latlng.lng); });
}

// "Xaricde evler" kateqoriyasi ucun olke -> seher -> rayon kaskad secimi
function wireAbroadLocationPicker(countriesData, initialCountry, initialCity, initialDistrict) {
  var categorySelect = document.getElementById('categorySelect');
  var abroadBlock = document.getElementById('abroadLocationFields');
  var cityField = document.getElementById('cityField');
  var districtField = document.getElementById('districtField');
  var cityInput = document.getElementById('cityInput');
  var districtInput = document.getElementById('districtInput');
  var countrySelect = document.getElementById('countrySelect');
  var abroadCitySelect = document.getElementById('abroadCitySelect');
  var abroadDistrictSelect = document.getElementById('abroadDistrictSelect');
  if (!categorySelect || !abroadBlock || !countrySelect) return;

  function fillCountries(selectedCode) {
    countrySelect.innerHTML = '';
    Object.keys(countriesData).forEach(function (code) {
      var opt = document.createElement('option');
      opt.value = code;
      opt.textContent = countriesData[code].flag + ' ' + countriesData[code].name;
      countrySelect.appendChild(opt);
    });
    if (selectedCode && countriesData[selectedCode]) countrySelect.value = selectedCode;
    fillCities(initialCity);
    initialCity = null;
  }

  function fillCities(selectedCity) {
    var country = countriesData[countrySelect.value];
    abroadCitySelect.innerHTML = '';
    if (country) {
      Object.keys(country.cities).forEach(function (city) {
        var opt = document.createElement('option');
        opt.value = city;
        opt.textContent = city;
        abroadCitySelect.appendChild(opt);
      });
    }
    if (selectedCity) abroadCitySelect.value = selectedCity;
    fillDistricts(initialDistrict);
    initialDistrict = null;
  }

  function fillDistricts(selectedDistrict) {
    var country = countriesData[countrySelect.value];
    abroadDistrictSelect.innerHTML = '<option value="">Seçilməyib</option>';
    var districts = (country && country.cities[abroadCitySelect.value]) || [];
    districts.forEach(function (d) {
      var opt = document.createElement('option');
      opt.value = d;
      opt.textContent = d;
      abroadDistrictSelect.appendChild(opt);
    });
    if (selectedDistrict) abroadDistrictSelect.value = selectedDistrict;
  }

  function toggleMode() {
    var abroadRadio = document.querySelector('input[name="type"][data-abroad="1"]');
    var isAbroad = (categorySelect.value === 'xaricdə evlər') || (abroadRadio && abroadRadio.checked);
    abroadBlock.style.display = isAbroad ? '' : 'none';
    if (cityField) cityField.style.display = isAbroad ? 'none' : '';
    if (districtField) districtField.style.display = isAbroad ? 'none' : '';
    if (cityInput) cityInput.disabled = isAbroad;
    if (districtInput) districtInput.disabled = isAbroad;
    countrySelect.disabled = !isAbroad;
    abroadCitySelect.disabled = !isAbroad;
    abroadDistrictSelect.disabled = !isAbroad;
  }

  countrySelect.addEventListener('change', function () { fillCities(); });
  abroadCitySelect.addEventListener('change', function () { fillDistricts(); });
  categorySelect.addEventListener('change', toggleMode);
  window.__toggleAbroadMode = toggleMode;

  fillCountries(initialCountry);
  toggleMode();
}

// Marka -> model xeritesi (esas modeller, secilmis marka ucun model teklifleri gosterir)
var MAKE_MODELS = {
  "Mercedes-Benz": ["A-Class", "B-Class", "C-Class", "E-Class", "S-Class", "CLA", "CLS", "GLA", "GLB", "GLC", "GLE", "GLS", "G-Class", "V-Class", "Sprinter", "Vito", "AMG GT", "EQC", "EQE", "EQS"],
  "BMW": ["1 Series", "2 Series", "3 Series", "4 Series", "5 Series", "6 Series", "7 Series", "8 Series", "X1", "X2", "X3", "X4", "X5", "X6", "X7", "M3", "M5", "M4", "i3", "i4", "i7", "iX"],
  "Audi": ["A1", "A3", "A4", "A5", "A6", "A7", "A8", "Q2", "Q3", "Q5", "Q7", "Q8", "TT", "R8", "e-tron", "RS6", "S3", "S4"],
  "Volkswagen": ["Polo", "Golf", "Jetta", "Passat", "Arteon", "Tiguan", "Touareg", "Atlas", "T-Roc", "T-Cross", "ID.4", "Caddy", "Transporter"],
  "Toyota": ["Corolla", "Camry", "Yaris", "Avalon", "Prius", "RAV4", "Highlander", "4Runner", "Land Cruiser", "Land Cruiser Prado", "Hilux", "Fortuner", "C-HR", "Venza", "Sienna"],
  "Hyundai": ["Accent", "Elantra", "Sonata", "Azera", "i10", "i20", "i30", "i40", "Tucson", "Santa Fe", "Creta", "Palisade", "Kona", "Venue", "Staria"],
  "Kia": ["Picanto", "Rio", "Cerato", "Forte", "K5", "Stinger", "Sportage", "Sorento", "Telluride", "Soul", "Niro", "Seltos", "Carnival"],
  "Chevrolet": ["Spark", "Aveo", "Cruze", "Malibu", "Impala", "Camaro", "Corvette", "Captiva", "Equinox", "Traverse", "Tahoe", "Suburban", "Silverado"],
  "Ford": ["Fiesta", "Focus", "Fusion", "Mondeo", "Mustang", "EcoSport", "Kuga", "Escape", "Edge", "Explorer", "Expedition", "Ranger", "F-150", "Transit"],
  "Nissan": ["Micra", "Sentra", "Altima", "Maxima", "Versa", "Juke", "Qashqai", "X-Trail", "Murano", "Pathfinder", "Patrol", "Armada", "Navara", "370Z"],
  "Honda": ["Civic", "Accord", "City", "Insight", "HR-V", "CR-V", "Pilot", "Passport", "Fit", "Odyssey", "Ridgeline"],
  "Mazda": ["Mazda2", "Mazda3", "Mazda6", "CX-3", "CX-5", "CX-9", "CX-30", "MX-5"],
  "Lexus": ["IS", "ES", "GS", "LS", "RC", "NX", "RX", "GX", "LX", "UX"],
  "Porsche": ["911", "718 Cayman", "718 Boxster", "Panamera", "Macan", "Cayenne", "Taycan"],
  "Land Rover": ["Range Rover", "Range Rover Sport", "Range Rover Evoque", "Range Rover Velar", "Discovery", "Discovery Sport", "Defender"],
  "Lada (VAZ)": ["2101", "2105", "2106", "2107", "2109", "2110", "2114", "2115", "Priora", "Granta", "Vesta", "Largus", "Niva", "XRAY"],
  "GAZ": ["Volga", "Gazelle", "Sobol"],
  "UAZ": ["Patriot", "Hunter", "Pickup", "Buhanka (452)"],
  "Opel": ["Corsa", "Astra", "Insignia", "Vectra", "Zafira", "Mokka", "Grandland", "Crossland"],
  "Skoda": ["Fabia", "Octavia", "Superb", "Rapid", "Kodiaq", "Karoq", "Kamiq"],
  "Renault": ["Clio", "Megane", "Symbol", "Logan", "Sandero", "Duster", "Kadjar", "Talisman", "Fluence"],
  "Peugeot": ["208", "301", "308", "408", "508", "2008", "3008", "5008", "Partner"],
  "Citroen": ["C3", "C4", "C5", "C-Elysee", "Berlingo", "Cactus"],
  "Fiat": ["Punto", "Tipo", "Egea", "500", "Panda", "Doblo", "Linea"],
  "Mitsubishi": ["Lancer", "Outlander", "ASX", "Pajero", "Pajero Sport", "L200", "Eclipse Cross"],
  "Subaru": ["Impreza", "Legacy", "Outback", "Forester", "XV", "WRX", "BRZ"],
  "Suzuki": ["Swift", "Baleno", "Vitara", "Grand Vitara", "Jimny", "SX4", "Ertiga"],
  "Volvo": ["S60", "S90", "V40", "V60", "V90", "XC40", "XC60", "XC90"],
  "Jeep": ["Renegade", "Compass", "Cherokee", "Grand Cherokee", "Wrangler", "Gladiator"],
  "Mini": ["Cooper", "Cooper S", "Clubman", "Countryman", "Paceman"],
  "Infiniti": ["Q50", "Q60", "Q70", "QX50", "QX60", "QX70", "QX80"],
  "Cadillac": ["ATS", "CTS", "CT5", "CT6", "XT4", "XT5", "XT6", "Escalade"],
  "Chrysler": ["300", "Pacifica", "Voyager"],
  "Dodge": ["Charger", "Challenger", "Durango", "Journey", "Grand Caravan"],
  "GMC": ["Terrain", "Acadia", "Yukon", "Sierra", "Canyon"],
  "Yamaha": ["MT-03", "MT-07", "MT-09", "MT-10", "YZF-R1", "YZF-R6", "YZF-R3", "XMAX", "NMAX", "Tenere 700"],
  "Kawasaki": ["Ninja 400", "Ninja 650", "Ninja ZX-6R", "Ninja ZX-10R", "Z650", "Z900", "Versys 650", "Vulcan S"],
  "Harley-Davidson": ["Iron 883", "Forty-Eight", "Street Bob", "Fat Boy", "Road King", "Street Glide", "Sportster S"],
  "Iveco": ["Daily", "Eurocargo", "Stralis"],
  "MAN": ["TGX", "TGS", "TGL", "TGE"],
  "Scania": ["R-series", "S-series", "P-series", "G-series"],
  "Isuzu": ["D-Max", "NPR", "Trooper", "MU-X"]
};

function wireMakeModelCascade(makeEl, modelDatalistEl) {
  if (!makeEl || !modelDatalistEl) return;
  function refresh() {
    var models = MAKE_MODELS[makeEl.value] || [];
    modelDatalistEl.innerHTML = '';
    models.forEach(function (m) {
      var opt = document.createElement('option');
      opt.value = m;
      modelDatalistEl.appendChild(opt);
    });
  }
  makeEl.addEventListener('change', refresh);
  refresh();
}

// Turbo.az meqli klikoluna bilen model seti (yalniz Elan yerlesdir sehifesinde istifade olunur)
function wireMakeModelGrid(makeEl, inputEl, gridEl) {
  if (!makeEl || !inputEl || !gridEl) return;
  var VISIBLE_COUNT = 15;
  var expanded = false;

  function render() {
    var models = MAKE_MODELS[makeEl.value] || [];
    gridEl.innerHTML = '';
    if (!models.length) return;
    var shown = expanded ? models : models.slice(0, VISIBLE_COUNT);
    shown.forEach(function (m) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'model-grid-item';
      btn.textContent = m;
      if (inputEl.value === m) btn.classList.add('selected');
      btn.addEventListener('click', function () {
        inputEl.value = m;
        gridEl.querySelectorAll('.model-grid-item').forEach(function (b) { b.classList.remove('selected'); });
        btn.classList.add('selected');
        inputEl.dispatchEvent(new Event('change', { bubbles: true }));
        inputEl.dispatchEvent(new Event('input', { bubbles: true }));
      });
      gridEl.appendChild(btn);
    });
    if (!expanded && models.length > VISIBLE_COUNT) {
      var allBtn = document.createElement('button');
      allBtn.type = 'button';
      allBtn.className = 'model-grid-allbtn';
      allBtn.textContent = 'Bütün modellər';
      allBtn.addEventListener('click', function () { expanded = true; render(); });
      gridEl.appendChild(allBtn);
    }
  }

  makeEl.addEventListener('change', function () { expanded = false; inputEl.value = ''; render(); });
  render();
}

wireMakeModelCascade(document.getElementById('makeSelect'), document.getElementById('modelList'));
wireMakeModelCascade(document.getElementById('filterMakeSelect'), document.getElementById('filterModelList'));

// Sevimlilere elave / cixar (AJAX)
document.querySelectorAll('.fav-btn').forEach(function (btn) {
  btn.addEventListener('click', function (e) {
    e.preventDefault();
    var id = btn.dataset.id;
    fetch('/api/sevimli/' + id, { method: 'POST' })
      .then(function (r) {
        if (r.status === 401 || r.redirected) { window.location.href = '/giris'; return null; }
        return r.json();
      })
      .then(function (data) {
        if (!data) return;
        btn.classList.toggle('active', data.is_favorite);
      });
  });
});

// Muqayise duymesi (kartlarda)
document.querySelectorAll('.compare-btn').forEach(function (btn) {
  btn.addEventListener('click', function (e) {
    e.preventDefault();
    e.stopPropagation();
    var id = btn.dataset.id;
    var isActive = btn.classList.contains('active');
    var url = (isActive ? '/muqayise/cixar/' : '/muqayise/elave/') + id;
    fetch(url, { method: 'POST' })
      .then(function () { window.location.reload(); });
  });
});

// Yeni elan formu: emlak / neqliyyat sahelerini dinamik gosterme
var typeRadios = document.querySelectorAll('input[name="type"]');
var propertyFields = document.getElementById('propertyFields');
var vehicleFields = document.getElementById('vehicleFields');
var categorySelect = document.getElementById('categorySelect');
var titleInput = document.getElementById('titleInput');

var PROPERTY_CATS = ["mənzil", "həyət evi/bağ evi", "ofis", "qaraj", "torpaq", "obyekt"];
var VEHICLE_CATS = ["minik", "suv", "moto", "pikap", "furqon", "kommersiya", "ehtiyat hissələri"];
var PROPERTY_TITLE_PLACEHOLDER = "məs. Yasamalda 3 otaqlı təmirli mənzil";
var VEHICLE_TITLE_PLACEHOLDER = "məs. Hyundai Tucson, 2021";

function refreshFormForType(type) {
  if (!propertyFields) return;
  if (type === 'emlak') {
    propertyFields.style.display = '';
    vehicleFields.style.display = 'none';
    fillCategories(PROPERTY_CATS);
    if (titleInput) titleInput.placeholder = PROPERTY_TITLE_PLACEHOLDER;
  } else {
    propertyFields.style.display = 'none';
    vehicleFields.style.display = '';
    fillCategories(VEHICLE_CATS);
    if (titleInput) titleInput.placeholder = VEHICLE_TITLE_PLACEHOLDER;
  }
  if (typeof window.__toggleAbroadMode === 'function') window.__toggleAbroadMode();
  renderSubcatButtons();
  if (typeof repositionSharedFields === 'function') repositionSharedFields(type);
  var imagesReqMark = document.getElementById('imagesReqMark');
  if (imagesReqMark) imagesReqMark.style.display = (type === 'neqliyyat') ? '' : 'none';
}

// Kateqoriya sechimini vizual duyme seklinde gosterir (categorySelect ile senkron)
function renderSubcatButtons() {
  var container = document.getElementById('subcatGrid');
  if (!container || !categorySelect) return;
  container.innerHTML = '';
  Array.prototype.forEach.call(categorySelect.options, function (opt) {
    var btn = document.createElement('div');
    btn.className = 'subcat-item' + (opt.selected ? ' selected' : '');
    btn.textContent = opt.textContent;
    btn.addEventListener('click', function () {
      categorySelect.value = opt.value;
      renderSubcatButtons();
      toggleSparePartsMode();
    });
    container.appendChild(btn);
  });
  toggleSparePartsMode();
}

// "Ehtiyat hisseleri" kateqoriyasi secilende tam avtomobil sirasi evezine
// sade sahe qrupunu gosterir (ve gizli olan terefin inputlarini deaktiv edir ki, cixariş qarismasin)
function toggleSparePartsMode() {
  var spareEl = document.getElementById('sparePartFields');
  var vehicleEl = document.getElementById('vehicleFields');
  var sharedBlock = document.getElementById('sharedFieldsBlock');
  if (!spareEl || !vehicleEl || !categorySelect) return;
  var isSparePart = categorySelect.value === 'ehtiyat hissələri';

  spareEl.style.display = isSparePart ? '' : 'none';
  spareEl.querySelectorAll('input, select').forEach(function (el) { el.disabled = !isSparePart; });

  vehicleEl.style.display = isSparePart ? 'none' : '';
  vehicleEl.querySelectorAll('input, select').forEach(function (el) {
    // yalnid acilmis (locked olmayan) addimlardaki sahələri deaktiv/aktiv et,
    // qalanlar artiq oz ardicilliq mentiqi ile idare olunur; turbo-step xaricindeki
    // saheler (mes. Emeliyyat secimi) hemise adi qaydada aktiv/deaktiv olunur
    var step = el.closest('.turbo-step');
    if (isSparePart) { el.disabled = true; }
    else if (!step) { el.disabled = false; }
    else if (!step.classList.contains('locked')) { el.disabled = false; }
  });

  // Paylasilan saheler (basliq/qiymet/seher...) hemise GORUNEN bloka kocurulmelidir
  if (sharedBlock && document.getElementById('makeSelect') && document.getElementById('makeSelect').closest('.turbo-wizard')) {
    var target = isSparePart ? spareEl : vehicleEl;
    if (sharedBlock.parentElement !== target && target.style.display !== 'none') {
      target.appendChild(sharedBlock);
    }
  }
}

// Tip kartlarinin (Emlak/Neqliyyat/Xaricde menzil) vizual "selected" veziyyeti
function syncTypeCards() {
  document.querySelectorAll('.type-card').forEach(function (card) {
    var input = card.querySelector('input[type="radio"]');
    if (input) card.classList.toggle('selected', input.checked);
  });
}
document.querySelectorAll('.type-card input[type="radio"]').forEach(function (r) {
  r.addEventListener('change', syncTypeCards);
});
syncTypeCards();

// Addim-addim (wizard) naviqasiyasi - Elan yerlesdir sehifesi
function wireWizard() {
  var steps = document.querySelectorAll('.wizard-step-section');
  var stepItems = document.querySelectorAll('.step-item');
  var stepLines = document.querySelectorAll('.step-line');
  var backBtn = document.getElementById('wizardBack');
  var nextBtn = document.getElementById('wizardNext');
  var submitBtn = document.getElementById('wizardSubmit');
  var indicator = document.getElementById('stepIndicator');
  if (!steps.length || !nextBtn) return;
  var current = 1;
  var total = steps.length;
  var isFirstRender = true;

  function render() {
    steps.forEach(function (s) { s.classList.toggle('active', parseInt(s.dataset.step, 10) === current); });
    stepItems.forEach(function (item) {
      var n = parseInt(item.dataset.step, 10);
      item.classList.toggle('active', n === current);
      item.classList.toggle('done', n < current);
    });
    stepLines.forEach(function (line, idx) { line.classList.toggle('done', (idx + 1) < current); });
    backBtn.style.visibility = current === 1 ? 'hidden' : 'visible';
    nextBtn.style.display = current === total ? 'none' : 'inline-flex';
    submitBtn.style.display = current === total ? 'inline-flex' : 'none';
    if (current === total) updateReview();
    if (indicator && !isFirstRender) window.scrollTo({ top: indicator.offsetTop - 90, behavior: 'smooth' });
    isFirstRender = false;
  }

  function validateStep(n) {
    if (n === 2) {
      var title = document.getElementById('titleInput');
      var price = document.getElementById('priceInput');
      var cityInput = document.getElementById('cityInput');
      if (title && !title.reportValidity()) return false;
      if (price && !price.reportValidity()) return false;
      if (cityInput && !cityInput.disabled && !cityInput.reportValidity()) return false;
    }
    return true;
  }

  function updateReview() {
    var title = document.getElementById('titleInput');
    var price = document.getElementById('priceInput');
    var cityInput = document.getElementById('cityInput');
    var abroadCity = document.getElementById('abroadCitySelect');
    var reviewTitle = document.getElementById('reviewTitle');
    var reviewPrice = document.getElementById('reviewPrice');
    var reviewCity = document.getElementById('reviewCity');
    if (reviewTitle) reviewTitle.textContent = (title && title.value) || '—';
    if (reviewPrice) reviewPrice.textContent = (price && price.value) ? price.value + ' AZN' : '—';
    var cityVal = (cityInput && !cityInput.disabled) ? cityInput.value : (abroadCity ? abroadCity.value : '');
    if (reviewCity) reviewCity.textContent = cityVal || '—';
  }

  nextBtn.addEventListener('click', function () {
    if (!validateStep(current)) return;
    if (current < total) { current++; render(); }
  });
  backBtn.addEventListener('click', function () {
    if (current > 1) { current--; render(); }
  });

  render();
}

function fillCategories(list) {
  if (!categorySelect) return;
  categorySelect.innerHTML = '';
  list.forEach(function (c) {
    var opt = document.createElement('option');
    opt.value = c;
    opt.textContent = c[0].toUpperCase() + c.slice(1);
    categorySelect.appendChild(opt);
  });
}

if (typeRadios.length) {
  typeRadios.forEach(function (r) {
    r.addEventListener('change', function () {
      refreshFormForType(r.value);
      var categoryField = document.getElementById('categoryField');
      var abroadCatInput = document.getElementById('abroadCategoryInput');
      var residenceField = document.getElementById('residenceField');
      if (r.dataset.abroad === '1') {
        if (categorySelect) categorySelect.disabled = true;
        if (abroadCatInput) abroadCatInput.disabled = false;
        if (categoryField) categoryField.style.display = 'none';
        if (residenceField) residenceField.style.display = 'none';
        if (typeof window.__toggleAbroadMode === 'function') window.__toggleAbroadMode();
      } else {
        if (categorySelect) categorySelect.disabled = false;
        if (abroadCatInput) abroadCatInput.disabled = true;
        if (categoryField) categoryField.style.display = '';
        if (residenceField) residenceField.style.display = '';
      }
    });
  });
  var checked = document.querySelector('input[name="type"]:checked');
  refreshFormForType(checked ? checked.value : 'emlak');
}

// Detal sehifesinde qalereya
document.querySelectorAll('.gallery-thumbs img').forEach(function (thumb) {
  thumb.addEventListener('click', function () {
    var main = document.querySelector('.gallery-main img');
    if (main) main.src = thumb.src;
  });
});
