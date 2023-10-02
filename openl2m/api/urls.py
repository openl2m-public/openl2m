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
from django.urls import path, register_converter

# from django.conf.urls import url

from api.views import (
    InterfaceArpView,
    ApiBasicsView,
)


class InterfaceNameConvertor:
    # convertor class to make sure interface names follow url-safe formats
    regex = '[a-zA-Z0-9\/_\-]*'

    def to_python(self, value):
        # replace _ with /
        return value.replace("_", "/")

    def to_url(self, value):
        # replace / with _
        return value.replace("/", "_")


register_converter(InterfaceNameConvertor, 'ifname')

app_name = 'api'
urlpatterns = [
    path('', views.api, name='api'),
    path('<int:group_id>/<int:switch_id>/', ApiBasicsView.as_view(), name='api_basics'),
    path('<int:group_id>/<int:switch_id>/<ifname:interface_name>/arp/', InterfaceArpView.as_view(), name='api_interface_arp'),
]
