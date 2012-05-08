# Create your views here.
from django.template import Context, loader
from userside.models import *
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import render_to_response
from datetime import datetime
from django.utils import timezone, simplejson
from userside.stats import *
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
import re

def test_active_calls(request, company_id):
	calls = active_calls(company_id)
	#calls = Call.objects.all()
	t = loader.get_template('test/index.html')
	c = Context({'calls':calls})
	return HttpResponse(t.render(c))

def test_position(request, company_id, caller_id):
	return place_in_line(company_id, caller_id)
	
def splash(request):
	t = loader.get_template('bootstrap.html')
	
	#If redirected to the splash page with either input or a false tag (used only for '1' corner case)
	if (request.GET.has_key('input') or request.GET.has_key("false")):
		
		#Set input string (empty if false)
		if (request.GET.has_key("false")):
			input_string = ''
		else:
			input_string = request.GET.get('input')
		
		#Strip non-numbers
		caller_id = re.sub("\D", "", input_string)
		
		#Try and format as phone number (if more than 10 characters, ignore first (i.e. 1) and get next 10 characters)
		if (len(caller_id) >= 11):
			caller_id = caller_id[1:11]
		
		#If the customer exists, redirect to dashboard
		try:
			customer = Customer.objects.get(phone_number = caller_id)
			reverse_location = reverse('dashboard') + "?input=" + caller_id
			return redirect(reverse_location)
		#If the customer does not exist
		except Customer.DoesNotExist:
			#Try and find the company
			try:
				company = Company.objects.get(name__iexact = input_string)
				reverse_location = reverse('company') + "?input=" + input_string
				return redirect(reverse_location)
			except Company.DoesNotExist:
				c = Context({'statement': 'Sorry! We were unable to find that record.', 'fade': 'true'})
				
	else:
		c = Context({'statement': 'Where do you stand?', 'fade': 'true'})
	return HttpResponse(t.render(c))

def company(request):
	company_name = request.GET.get('input')
	
	#Fix crash on 1
	if (company_name == '1'):
		reverse_location = reverse('splash')  + "?false"
		return redirect(reverse_location)
	
	try:
		company = Company.objects.get(name__iexact = company_name)
	#Create new customer
	except Company.DoesNotExist:
		reverse_location = reverse('splash') + "?input=" + company_name
		return redirect(reverse_location)
	hour_range = range(24) #OPEN 9-5
	day_range = range(7) #7 Days/week
	line_length = len(active_calls(company))
	avg_serv = avg_serv_rate(company)
	avg_waits = avg_by_day_hour_range(company, True, True, hour_range, day_range)
	reps = working_reps(company)
	estimate = round(est_wait(avg_serv, reps, line_length), 0)
	if estimate == 0:
		estimate = 1
	avg_waits = []
	# for i in day_range:
	# 	avg_waits.append([1]*len(hour_range))
	for i in range(len(avg_waits)):
		avg_waits[i] = avg_waits[i][9:18]
	
	return render_to_response('bootstrap-company.html', {'line_length':line_length, 'estimate':estimate, 'avg_waits': avg_waits, 'phone_number':company.phone_number, 'website':company.website_link, 'desc':company.description})
	
def dashboard(request):
	caller_id = request.GET.get('input')
	
	#Fix crash on 1
	if (caller_id == '1'):
		reverse_location = reverse('splash')  + "?false"
		return redirect(reverse_location)
	
	
	xhr = request.GET.has_key('xhr')
	response_dict = {}
	try:
		customer = Customer.objects.get(phone_number = caller_id)
	except Customer.DoesNotExist:
		reverse_location = reverse('splash') + "?input=" + caller_id
		return redirect(reverse_location)
	
	
	company   = active_company(caller_id)
	position  = place_in_line(company, caller_id)
	avg_waits = avg_wait_naive(company,9,18)
	avg_serv  = avg_serv_rate(company)
	reps      = working_reps(company)
	estimate  = est_wait(avg_serv,reps,position)
	estimate  = round(estimate, 0)
	if estimate == 0:
	  estimate = 1
	
	response_dict.update({'position':position, 'avg_waits':avg_waits, 'est_wait':estimate})

	if xhr:
		return HttpResponse(simplejson.dumps(response_dict), mimetype='application/javascript')
	
	return render_to_response('bootstrap-dashboard.html', response_dict);

def callslist(request):
	calls = Call.objects.all()
	t = loader.get_template('callslist.html')
	c = Context({'calls':calls})
	return HttpResponse(t.render(c))

def testcalls(request):
	t = loader.get_template('test.html')
	c = Context()
	return HttpResponse(t.render(c))
		
# return list of avg waits for this d.o.w. from start_hr to < end_hr
def avg_wait_naive(company,start_hr,end_hr):
  avg_wait_day_hour = avg_by_day_hour(company,True,True)
  day = datetime.now().weekday()
  return avg_wait_day_hour[day][start_hr:end_hr]

# return avg service time for this d.o.w. and hour
def avg_serv_rate(company):
  avg_serv_day_hour = avg_by_day_hour(company,True,False) 
  day = datetime.now()
  return avg_serv_day_hour[day.weekday()][day.hour]

def est_wait(avg_serv,reps,position):
  return (avg_serv * position) / reps



def call_api(request, company_id, caller_id):
	
	
	#Check if customer exists
	try:
		customer = Customer.objects.get(phone_number = caller_id)
	#Create new customer
	except Customer.DoesNotExist:
		customer = Customer(phone_number = caller_id)
		customer.save()
	
	prev_calls = Call.objects.filter(customer = customer).order_by('-callstart')

	if (len(prev_calls) > 0):
		if (not prev_calls[0].callend):
			return HttpResponse("There is already an active call from this number")
	
	#Check if company exists
	try:
		company = Company.objects.get(id = company_id)
	#This should not happen, exit
	except Company.DoesNotExist:
		return HttpResponse("Company " + company_id + " does not exist.")
	
	#Create new call
	call = Call(callstart = timezone.now(), customer=customer, company=company)
	call.save()
	return HttpResponse("Call at " + str(call.callstart))

def pickup_api(request, company_id, rep_id, caller_id):
	#Check if customer exists
	try:
		customer = Customer.objects.get(phone_number = caller_id)
	#This should not happen, exit
	except Customer.DoesNotExist:
		return HttpResponse("Customer " + caller_id + " does not exist.")
		
	#Check if company exists
	try:
		company = Company.objects.get(id = company_id)
	#This should not happen, exit
	except Company.DoesNotExist:
		return HttpResponse("Company " + company_id + " does not exist.")
		
	#Check if representative exists
	try:
		rep = Representative.objects.get(internal_id = rep_id)
	#This should not happen, exit
	except Representative.DoesNotExist:
		return HttpResponse("Rep " + rep_id + " does not exist.")
	
	#Try and get the most recent call
	try:
		call = Call.objects.filter(customer = customer).order_by('-callstart')[0] #FIRST OR LAST??
	#This should not happen
	except Call.DoesNotExist:
		return HttpResponse("Call " + caller_id + " does not exist.")
	
	if(call.callend):
		return HttpResponse("Call already picked up")
	if(call.callend):
		return HttpResponse("Call already ended")			

	call.rep = rep
	call.callanswered = timezone.now()
	call.save()
	return HttpResponse("Call picked up at " + str(call.callanswered))

def hangup_api(request, company_id, caller_id):
	#Check if customer exists
	try:
		customer = Customer.objects.get(phone_number = caller_id)
	#This should not happen, exit
	except Customer.DoesNotExist:
		return HttpResponse("Customer " + caller_id + " does not exist.")
		
	#Check if company exists
	try:
		company = Company.objects.get(id = company_id)
	#This should not happen, exit
	except Company.DoesNotExist:
		return HttpResponse("Company " + company_id + " does not exist.")
	
	#Try and get the most recent call
	try:
		call = Call.objects.filter(customer = customer).order_by('-callstart')[0] #FIRST OR LAST??
	#This should not happen
	except Call.DoesNotExist:
		return HttpResponse("Call " + caller_id + " does not exist.")
	
	if (call.callend):
		return HttpResponse("Call already ended")
	
	call.callend = timezone.now()
	call.save()
	return HttpResponse("Call ended at " + str(call.callend))
	
