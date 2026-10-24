from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_safe
from .district_data import MEASURES
from .repository import district_rows
from .curation import crop_options, resolve_crop
from django.db import DatabaseError
from django.core.exceptions import ObjectDoesNotExist, ImproperlyConfigured


@require_safe
def district_statistics(request):
    try:
        rows=district_rows(settings.PUBLIC_EVIDENCE_ROOT)
    except (OSError,ValueError,KeyError,DatabaseError,ObjectDoesNotExist,ImproperlyConfigured):
        return render(request,'evidence/district_unavailable.html',status=503)
    province_id=request.GET.get('province','')
    district_id=request.GET.get('district','')
    crop=request.GET.get('crop','')
    provinces=sorted({(r['province_id'],r['province']) for r in rows})
    if province_id and province_id not in dict(provinces):raise Http404('Unknown province')
    districts=sorted({(r['district_id'],r['district']) for r in rows if r['province_id']==province_id},key=lambda x:x[1])
    if district_id and district_id not in dict(districts):raise Http404('District is not in selected province')
    district_crop_rows=[r for r in rows if r['district_id']==district_id] if district_id else []
    crops=crop_options(district_crop_rows)
    if crop:
        try:crop=resolve_crop(crop,district_crop_rows)
        except ValueError:raise Http404('Crop unavailable for selected district')
    selected=[r for r in district_crop_rows if r['crop_code']==crop] if crop else []
    selected.sort(key=lambda r:list(MEASURES).index(r['measure']))
    return render(request,'evidence/district.html',dict(provinces=provinces,districts=districts,crops=crops,
        province_id=province_id,district_id=district_id,crop=crop,crop_name=dict(crops).get(crop,''),selected=selected,
        province_name=dict(provinces).get(province_id,''),district_name=dict(districts).get(district_id,'')))
