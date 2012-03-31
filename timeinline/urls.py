from django.conf.urls import patterns, include, url
import os

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    url(r'^$', 'userside.views.splash', name='splash'),
    url(r'^dashboard/(?P<caller_id>\d+)/$', 'userside.views.dashboard'),
	
	#API CALLS
	#url.com/api/call/company_id/caller_id
	url(r'^api/call/(?P<company_id>\d+)/(?P<caller_id>\d+)/$', 'userside.views.call_api'),
	
	#url.com/api/pickup/company_id/rep_id/caller_id
	url(r'^api/pickup/(?P<company_id>\d+)/(?P<rep_id>\d+)/(?P<caller_id>\d+)/$', 'userside.views.pickup_api'),
	
	#url.com/api/hangup/company_id/caller_id
	url(r'^api/hangup/(?P<company_id>\d+)/(?P<caller_id>\d+)/$', 'userside.views.hangup_api'),
	
    # url(r'^timeinline/', include('timeinline.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)
