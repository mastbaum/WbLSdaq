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

#ifndef Digitizer__hh
#define Digitizer__hh

#include <vector>

#include "VMECard.hh"
#include "Buffer.hh"
#include <H5Cpp.h>

class DigitizerSettings {

    public:

        DigitizerSettings(std::string _index) : index(_index) {}
        
        virtual ~DigitizerSettings() {}
        
        inline std::string getIndex() { return index; }
        
    protected:
    
        std::string index;

};

class Digitizer : public VMECard {

    public:   
    
        Digitizer(BoardCommManager &bridge, uint32_t baseaddr) : VMECard(bridge, baseaddr) {}
        
        virtual ~Digitizer() {}
    
        virtual bool program(DigitizerSettings &settings) = 0;
        
        virtual bool checkTemps(std::vector<uint32_t> &temps, uint32_t danger) = 0;
        
        virtual void softTrig() = 0;
        
        virtual void startAcquisition() = 0;
        
        virtual void stopAcquisition() = 0;
        
        virtual bool acquisitionRunning() = 0;
        
        virtual bool readoutReady() = 0;
        
        virtual size_t readoutBLT(char *buffer, size_t buffer_size);
 
};

inline void writeall(const int fd, const void *ptr, int len) {
    uint8_t *dat = (uint8_t*)ptr;
    while (len) {
        int res = write(fd,dat,len);
        if (res < 0) throw std::runtime_error("writeall failed: "+std::to_string(res));
        len -= res;
        dat += res;
    }
}

typedef struct DigitizerData {
  typedef struct ChannelData {
    uint32_t chID;
    uint32_t offset;
    uint32_t threshold;
    float dynamic_range;
    uint16_t samples[20][500];
    uint16_t patterns[20];
  } ChannelData;

  uint16_t type;
  uint16_t bits;
  uint16_t samples;
  uint16_t nEvents;
  float ns_sample;
  uint32_t counters[20];
  uint32_t timetags[20];
  uint16_t exttimetags[20];

  ChannelData channels[16];
} DigitizerData;

class Decoder {
    
    public:
        virtual ~Decoder() {}
        
        virtual void decode(Buffer &buffer) = 0;
        
        virtual size_t eventsReady() = 0;
        
        virtual void writeOut(H5::H5File &file, size_t nEvents) = 0;

        virtual DigitizerSettings* getSettings() { return nullptr; }

        virtual void pack(DigitizerData* data, size_t nEvents) {}
};

#endif

