# views.py
import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


@require_http_methods(["POST"])
@csrf_exempt
def initialize_payment(request):
    try:
        amount = request.POST.get("amount")
        email = request.POST.get("email")

        if not amount or not email:
            return JsonResponse({"message": "Missing required parameters."}, status=400)

        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        data = {
            "amount": int(amount) * 100,  # Paystack uses kobo
            "email": email,
            "callback_url": "https://yourdomain.com/paystack/callback/",  # adjust to your frontend/server route
        }

        response = requests.post("https://api.paystack.co/transaction/initialize", json=data, headers=headers)
        resp_json = response.json()

        if response.status_code == 200 and resp_json.get("status"):
            return JsonResponse({
                "authorization_url": resp_json["data"]["authorization_url"],
                "access_code": resp_json["data"]["access_code"],
                "reference": resp_json["data"]["reference"],
            })
        return JsonResponse({"message": resp_json.get("message", "Initialization failed.")}, status=400)

    except requests.exceptions.RequestException:
        return JsonResponse({"message": "Network communication failed, try again."}, status=503)
    except Exception as e:
        return JsonResponse({"message": f"Unexpected error: {str(e)}"}, status=500)


@require_http_methods(["GET"])
@csrf_exempt
def verify_payment(request):
    reference = request.GET.get("reference")
    if not reference:
        return JsonResponse({"message": "Missing reference parameter."}, status=400)

    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
    }

    try:
        response = requests.get(f"https://api.paystack.co/transaction/verify/{reference}", headers=headers)
        resp_json = response.json()

        if resp_json.get("status") and resp_json["data"]["status"] == "success":
            return JsonResponse({"message": "Payment verified successfully.", "data": resp_json["data"]})
        else:
            return JsonResponse({"message": "Payment verification failed.", "data": resp_json.get("data", {})}, status=400)

    except requests.exceptions.RequestException:
        return JsonResponse({"message": "Network error while verifying payment."}, status=503)
