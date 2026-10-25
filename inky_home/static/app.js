const $ = selector => document.querySelector(selector);
let state, initialized = false, previewVersion, lessonVersion, busy = false;
function notice(message, error = false) {
  $('#notice').textContent = message;
  $('#notice').className = error ? 'error' : '';
  $('#notice').hidden = !message;
}
async function api(url, data) {
  const response = await fetch(url, data === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'The request could not be completed.');
  return result;
}
function settingsFields() {
  for (const field of ['units', 'rollover', 'timezone']) $('#' + field).value = state.settings[field];
}
async function refresh() {
  if (busy) return;
  busy = true;
  try {
    state = await api('/api/status');
    $('#connection').textContent = '● Connected';
    $('#mode').textContent = state.mode === 'preview' ? 'Mac preview' : 'Inky Impression · 4 inch';
    $('#display-status').textContent = state.display_error ? 'Display needs attention' : state.updating ? 'Refreshing display…' : state.pending ? 'Screen queued' : 'Up to date';
    $('#updated').textContent = state.last_display_at ? new Date(state.last_display_at).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}) : '—';
    $('#preview').onload = () => { $('#preview-wait').hidden = true; };
    if (state.preview_version && previewVersion !== state.preview_version) {
      $('#preview').src = '/api/preview.png?v=' + state.preview_version;
      previewVersion = state.preview_version;
    }
    const french = state.selection.app === 'french';
    $('#c-label').textContent = french ? 'Previous' : 'Today / 3 days';
    $('#d-label').textContent = french ? 'Next' : 'Update';
    for (const app of ['weather', 'french']) {
      $('[data-app="' + app + '"]').setAttribute('aria-pressed', String(state.selection.app === app));
      $('#' + app + '-active').textContent = state.selection.app === app ? 'On display' : '↗';
    }
    $('#weather-city').textContent = state.settings.city ? state.settings.city.name : 'Choose your city';
    $('#weather-status').textContent = state.sample ? 'Sample weather · for layout testing only' : state.fetching ? 'Fetching weather…' : state.weather_error ? state.weather_error : state.stale ? 'Cached forecast is out of date.' : state.weather ? 'Weather updated ' + new Date(state.weather.fetched_at).toLocaleString() : 'Choose a city to get your forecast.';
    $('#device-errors').textContent = [state.display_error, state.button_error].filter(Boolean).join('\n');
    $('#lesson-title').textContent = state.selection.browse_day ? 'French · ' + state.lesson_day : "Today's French";
    $('#lesson-theme').textContent = state.lesson.theme;
    if (lessonVersion !== state.lesson_day) {
    lessonVersion = state.lesson_day;
    $('#lesson-cards').replaceChildren(...state.lesson.cards.map(card => {
      const item = document.createElement('div'); item.className = 'lesson-item';
      for (const [tag, text] of [['small',card.kind],['strong',card.title],['p',card.meaning],['p',card.example],['p',card.translation],['p',card.note]]) {
        const node = document.createElement(tag); node.textContent = text; item.append(node);
      }
      return item;
    }));
    }
    $('#history-day').min = state.first_day;
    $('#history-day').max = state.today;
    if (!$('#history-day').value) $('#history-day').value = state.lesson_day;
    if (!initialized) { settingsFields(); initialized = true; }
  } catch (error) {
    $('#connection').textContent = '● Disconnected';
    $('#display-status').textContent = 'Cannot reach dashboard · retrying';
  } finally { busy = false; }
}
async function act(url, data, message = '') {
  try { await api(url, data); notice(message); await refresh(); return true; }
  catch (error) { notice(error.message, true); return false; }
}
document.querySelectorAll('[data-button]').forEach(button => button.addEventListener('click', () => act('/api/action', {button:button.dataset.button})));
document.querySelectorAll('[data-app]').forEach(button => button.addEventListener('click', () => act('/api/app', {app:button.dataset.app})));
$('#settings-form').addEventListener('submit', event => {
  event.preventDefault();
  act('/api/settings', {units:$('#units').value, timezone:$('#timezone').value.trim(), rollover:$('#rollover').value}, 'Preferences saved.');
});
$('#city-form').addEventListener('submit', async event => {
  event.preventDefault();
  $('#search-button').disabled = true;
  $('#city-results').textContent = 'Searching…';
  try {
    const data = await api('/api/cities?q=' + encodeURIComponent($('#city-query').value.trim()));
    $('#city-results').replaceChildren();
    if (!data.results.length) $('#city-results').textContent = 'No cities found. Try another spelling.';
    for (const city of data.results) {
      const button = document.createElement('button'); button.type = 'button';
      button.textContent = [city.name, city.region, city.country].filter(Boolean).join(', ');
      button.addEventListener('click', async () => {
        button.disabled = true;
        if (await act('/api/settings', {city}, 'Location saved. Fetching your forecast…')) {
          $('#city-results').replaceChildren(); settingsFields();
        } else { button.disabled = false; }
      });
      $('#city-results').append(button);
    }
  } catch (error) { $('#city-results').textContent = error.message; }
  finally { $('#search-button').disabled = false; }
});
$('#history-form').addEventListener('submit', event => { event.preventDefault(); act('/api/french/day', {day:$('#history-day').value}); });
$('#today').addEventListener('click', () => act('/api/french/day', {day:null}));
refresh(); setInterval(refresh, 3000);
