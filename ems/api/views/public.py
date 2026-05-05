from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ems.features import FEATURES_DATA


class FeaturesIndexView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        results = [
            {"slug": slug, "title": data["title"], "subtitle": data["subtitle"], "icon": data.get("icon")}
            for slug, data in FEATURES_DATA.items()
        ]
        return Response({"results": results})


class FeatureDetailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, slug):
        data = FEATURES_DATA.get(slug)
        if data is None:
            return Response({"detail": "Feature not found."}, status=404)
        return Response({"slug": slug, **data})
