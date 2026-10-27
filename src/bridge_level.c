#include <CoreAudio/CoreAudio.h>
#include <CoreFoundation/CoreFoundation.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc,char **argv) {
    int setUnity=argc==2 && !strcmp(argv[1],"--unity");
    AudioObjectPropertyAddress a={kAudioHardwarePropertyDevices,kAudioObjectPropertyScopeGlobal,kAudioObjectPropertyElementMain};
    UInt32 size=0;
    if(AudioObjectGetPropertyDataSize(kAudioObjectSystemObject,&a,0,NULL,&size)) return 1;
    AudioObjectID *ids=malloc(size);UInt32 count=size/sizeof(*ids);
    if(AudioObjectGetPropertyData(kAudioObjectSystemObject,&a,0,NULL,&size,ids)) {free(ids);return 1;}
    for(UInt32 i=0;i<count;i++) {
        CFStringRef name=NULL;UInt32 len=sizeof(name);
        a=(AudioObjectPropertyAddress){kAudioObjectPropertyName,kAudioObjectPropertyScopeGlobal,kAudioObjectPropertyElementMain};
        if(AudioObjectGetPropertyData(ids[i],&a,0,NULL,&len,&name)) continue;
        int match=CFEqual(name,CFSTR("POD HD300 USB Bridge 2ch"));CFRelease(name);
        if(!match) continue;
        a=(AudioObjectPropertyAddress){kAudioDevicePropertyVolumeScalar,kAudioDevicePropertyScopeInput,kAudioObjectPropertyElementMain};
        Float32 before=0,after=0;len=sizeof(before);
        if(AudioObjectGetPropertyData(ids[i],&a,0,NULL,&len,&before)) {free(ids);return 1;}
        if(setUnity) {
            Float32 unity=1;
            OSStatus err=AudioObjectSetPropertyData(ids[i],&a,0,NULL,sizeof(unity),&unity);
            if(err) {fprintf(stderr,"Cannot set bridge level: %d\n",(int)err);free(ids);return 1;}
        }
        len=sizeof(after);
        if(AudioObjectGetPropertyData(ids[i],&a,0,NULL,&len,&after)) {free(ids);return 1;}
        printf("{\"before_scalar\":%.9g,\"after_scalar\":%.9g,\"set_unity\":%s}\n",before,after,setUnity?"true":"false");
        free(ids);return 0;
    }
    fprintf(stderr,"HD300 bridge device not found\n");free(ids);return 1;
}
