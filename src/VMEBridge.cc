/**
 *  Copyright 2014 by Benjamin Land (a.k.a. BenLand100)
 *
 *  WbLSdaq is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  WbLSdaq is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with WbLSdaq. If not, see <http://www.gnu.org/licenses/>.
 */
 
#include "VMEBridge.hh"

using namespace std;

const std::string VMEBridge::error_codes[6] = {"Success","Bus Error","Comm Error","Generic Error","Invalid Param","Timeout Error"};

VMEBridge::VMEBridge(int link, int board) {
    this->link = link;
    this->board = board;
    int res = CAENVME_Init(cvV1718,link,board,&handle);
    if (res) {
        stringstream err;
        err << error_codes[-res] << " :: Could not open VME bridge!";
        throw runtime_error(err.str());
    }
}

VMEBridge::~VMEBridge() noexcept(false) {
    int res = CAENVME_End(handle);
    if (res) {
        stringstream err;
        err << error_codes[-res] << " :: Could not close VME bridge!";
        throw runtime_error(err.str());
    }
}
