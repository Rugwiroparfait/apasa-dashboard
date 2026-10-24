from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import render
from django.views.decorators.http import require_safe
from .public_data import FIGURES, SCENARIOS, SUMMARY_PATH, load_pilot

@require_safe
def home(request):
    return render(request, 'evidence/home.html')

@require_safe
def pilot(request):
    scenario = request.GET.get('scenario', 'all_reported')
    chart = request.GET.get('chart', next(iter(FIGURES.values())))
    if scenario not in SCENARIOS or chart not in FIGURES.values():
        raise Http404('Unknown published view')
    try:
        summaries, seed = load_pilot(settings.PUBLIC_EVIDENCE_ROOT)
    except (OSError, ValueError, KeyError, IndexError):
        return render(request, 'evidence/unavailable.html', status=503)
    return render(request, 'evidence/pilot.html', {'full': summaries['all_reported'], 'selected': summaries[scenario], 'summaries': summaries.values(), 'seed': seed, 'figures': FIGURES, 'chart': chart})

@require_safe
def figure(request, filename):
    if filename not in FIGURES.values():
        raise Http404('Unknown published figure')
    path = settings.PUBLIC_EVIDENCE_ROOT / 'outputs/day3/figures' / filename
    try:
        return FileResponse(path.open('rb'), content_type='image/png')
    except OSError:
        raise Http404('Published figure unavailable')

@require_safe
def summary_download(request):
    try:
        return FileResponse((settings.PUBLIC_EVIDENCE_ROOT / SUMMARY_PATH).open('rb'), as_attachment=True, filename='apasa_maize_overall_summary.csv', content_type='text/csv')
    except OSError:
        raise Http404('Published summary unavailable')
