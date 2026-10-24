from django.urls import path
from . import views
from .policy_views import policy_evidence, policy_workspace
from .district_views import district_statistics
app_name = 'evidence'
urlpatterns = [path('national-policy-evidence/crop/', policy_workspace, {'section': 'crop'}, name='policy-crop'), path('national-policy-evidence/note/', policy_workspace, {'section': 'note'}, name='policy-note'), path('national-policy-evidence/', policy_evidence, name='policy'), path('district-crop-statistics/', district_statistics, name='district-statistics'), path('', views.home, name='home'), path('evidence/maize/', views.pilot, name='pilot'), path('evidence/figures/<str:filename>/', views.figure, name='figure'), path('evidence/maize/summary.csv', views.summary_download, name='summary')]
