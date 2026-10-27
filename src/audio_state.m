#import <Foundation/Foundation.h>
#import <AVFoundation/AVFoundation.h>
#include <CoreAudio/CoreAudio.h>
int main(void) {
    @autoreleasepool {
        printf("Microphone authorization (0=undetermined,1=restricted,2=denied,3=authorized): %ld\n", (long)[AVCaptureDevice authorizationStatusForMediaType:AVMediaTypeAudio]);
        AudioObjectPropertyAddress a={kAudioHardwarePropertyDevices,kAudioObjectPropertyScopeGlobal,kAudioObjectPropertyElementMain};
        UInt32 size=0; AudioObjectGetPropertyDataSize(kAudioObjectSystemObject,&a,0,NULL,&size);
        AudioObjectID *ids=malloc(size); AudioObjectGetPropertyData(kAudioObjectSystemObject,&a,0,NULL,&size,ids);
        for(unsigned i=0;i<size/sizeof(AudioObjectID);i++) {
            CFStringRef name=NULL; UInt32 n=sizeof(name);
            a=(AudioObjectPropertyAddress){kAudioObjectPropertyName,kAudioObjectPropertyScopeGlobal,kAudioObjectPropertyElementMain};
            if(AudioObjectGetPropertyData(ids[i],&a,0,NULL,&n,&name)) continue;
            char text[256]; CFStringGetCString(name,text,sizeof(text),kCFStringEncodingUTF8); CFRelease(name);
            if(!strstr(text,"HD300")) continue;
            printf("Device %u: %s\n",ids[i],text);
            for(int input=0;input<2;input++) {
                a=(AudioObjectPropertyAddress){kAudioDevicePropertyVolumeScalar,input?kAudioDevicePropertyScopeInput:kAudioDevicePropertyScopeOutput,kAudioObjectPropertyElementMain};
                Float32 v=-1; UInt32 len=sizeof(v); OSStatus err=AudioObjectGetPropertyData(ids[i],&a,0,NULL,&len,&v);
                printf("%s volume=%f status=%d\n",input?"input":"output",v,(int)err);
                a.mSelector=kAudioDevicePropertyMute; UInt32 mute=999;len=sizeof(mute);
                err=AudioObjectGetPropertyData(ids[i],&a,0,NULL,&len,&mute);
                printf("%s mute=%u status=%d\n",input?"input":"output",mute,(int)err);
            }
        }
        free(ids);
    }
}
