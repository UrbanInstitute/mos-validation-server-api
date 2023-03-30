"""
Views for the users API.
"""
from knox.views import LoginView as KnoxLoginView
from rest_framework.authentication import BasicAuthentication
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.settings import api_settings
from rest_framework import generics
from rest_framework.response import Response
import rest_framework.permissions as permissions
from knox.models import AuthToken


from users.serializers import UserSerializer, LoginUserSerializer


class CreateUserView(generics.CreateAPIView):
    """Create a new user in the system"""
    serializer_class = UserSerializer


#class LoginView(KnoxLoginView):
#    authentication_classes = [BasicAuthentication,]
#    serializer_class = AuthTokenSerializer
#    permission_classes = (IsAuthenticated,)

class LoginView(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = [BasicAuthentication]

    serializer_class = LoginUserSerializer


    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        
        return Response({
            "user": UserSerializer(user, context=self.get_serializer_context()).data,
            "token": AuthToken.objects.create(user)[1]
        })




