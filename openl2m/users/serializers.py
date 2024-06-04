#
# This file is part of Open Layer 2 Management (OpenL2M).
#
# OpenL2M is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License version 3 as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.  You should have received a copy of the GNU General Public
# License along with OpenL2M. If not, see <http://www.gnu.org/licenses/>.
#
from django.contrib.auth.models import User
from rest_framework import serializers

from users.models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['user', 'bulk_edit']


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # fields = [
        #     'id',
        #     'username',
        #     'email',
        #     'first_name',
        #     'last_name',
        #     'is_active',
        #     'is_staff',
        #     'is_superuser',
        #     'last_login',
        #     'date_joined',
        # ]
        exclude = ['password']
