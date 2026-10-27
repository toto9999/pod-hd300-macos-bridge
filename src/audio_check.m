#import <Cocoa/Cocoa.h>
#import <AVFoundation/AVFoundation.h>
#include <CoreAudio/CoreAudio.h>
#include <math.h>

static AudioObjectID device=0;
static AudioDeviceIOProcID proc=NULL;
static double rate=48000, freq[2]={997,1499}, squares[2], sinSum[2], cosSum[2];
static uint64_t outFrames=0,inFrames=0,measured=0;
static NSString *reportPath;
static BOOL captureOnly=NO;
static float recorded[48000*5*2];
static uint64_t recordedFrames=0;

static OSStatus io(AudioObjectID dev,const AudioTimeStamp *now,const AudioBufferList *input,
                   const AudioTimeStamp *it,AudioBufferList *output,const AudioTimeStamp *ot,void *ctx) {
    UInt32 frames=0,channelBase=0;
    for(UInt32 b=0;output && b<output->mNumberBuffers;b++) {
        AudioBuffer *buf=&output->mBuffers[b];
        if(!buf->mData || !buf->mNumberChannels) continue;
        frames=buf->mDataByteSize/(sizeof(float)*buf->mNumberChannels);
        float *p=buf->mData;
        for(UInt32 f=0;f<frames;f++) for(UInt32 c=0;c<buf->mNumberChannels;c++)
            p[f*buf->mNumberChannels+c]=captureOnly?0:0.001*sin(2*M_PI*freq[(channelBase+c)%2]*(outFrames+f)/rate);
        channelBase+=buf->mNumberChannels;
    }
    outFrames+=frames;
    frames=0;channelBase=0;
    for(UInt32 b=0;input && b<input->mNumberBuffers;b++) {
        const AudioBuffer *buf=&input->mBuffers[b];
        if(!buf->mData || !buf->mNumberChannels) continue;
        frames=buf->mDataByteSize/(sizeof(float)*buf->mNumberChannels);
        const float *p=buf->mData;
        for(UInt32 f=0;f<frames;f++) {
            uint64_t n=inFrames+f;
            if(n<(uint64_t)(rate*0.5)) continue;
            for(UInt32 c=0;c<buf->mNumberChannels;c++) {
                UInt32 ch=channelBase+c;
                if(ch>1) continue;
                double x=p[f*buf->mNumberChannels+c], phase=2*M_PI*freq[ch]*n/rate;
                squares[ch]+=x*x;sinSum[ch]+=x*sin(phase);cosSum[ch]+=x*cos(phase);
                if(captureOnly && measured<48000*5) recorded[measured*2+ch]=(float)x;
            }
            if(b==0) measured++;
        }
        channelBase+=buf->mNumberChannels;
    }
    inFrames+=frames;
    recordedFrames=measured<48000*5?measured:48000*5;
    return noErr;
}

static void finish(NSString *error) {
    if(proc) { AudioDeviceStop(device,proc);AudioDeviceDestroyIOProcID(device,proc);proc=NULL; }
    if(captureOnly && recordedFrames) {
        NSString *wav=[[[reportPath stringByDeletingLastPathComponent] stringByDeletingLastPathComponent] stringByAppendingPathComponent:@"recordings/hal-diagnostic.wav"];
        FILE *file=fopen(wav.fileSystemRepresentation,"wb");
        if(file) {
            uint32_t bytes=(uint32_t)(recordedFrames*2*4),riff=36+bytes,size=16,hz=(uint32_t)rate,bytrate=hz*8;
            uint16_t format=3,channels=2,align=8,bits=32;
            fwrite("RIFF",1,4,file);fwrite(&riff,4,1,file);fwrite("WAVEfmt ",1,8,file);fwrite(&size,4,1,file);
            fwrite(&format,2,1,file);fwrite(&channels,2,1,file);fwrite(&hz,4,1,file);fwrite(&bytrate,4,1,file);
            fwrite(&align,2,1,file);fwrite(&bits,2,1,file);fwrite("data",1,4,file);fwrite(&bytes,4,1,file);
            fwrite(recorded,1,bytes,file);fclose(file);
        }
    }
    NSMutableArray *channels=[NSMutableArray array];BOOL passed=error==nil && measured>0;
    for(int ch=0;ch<2;ch++) {
        double rms=measured?sqrt(squares[ch]/measured):0;
        double amplitude=measured?2*hypot(sinSum[ch],cosSum[ch])/measured:0;
        BOOL ok=captureOnly?(rms>0):(rms>0.0005 && rms<0.001 && amplitude>0.0008 && amplitude<0.0012);
        passed=passed && ok;
        [channels addObject:@{@"frequency_hz":@(freq[ch]),@"rms":@(rms),@"tone_amplitude":@(amplitude),@"passed":@(ok)}];
    }
    NSDictionary *report=@{@"passed":@(passed),@"mode":captureOnly?@"capture-usb-bridge":@"synthetic-loopback",@"error":error?:[NSNull null],@"sample_rate":@(rate),
        @"measured_frames":@(measured),@"channels":channels,
        @"microphone_authorization":@([AVCaptureDevice authorizationStatusForMediaType:AVMediaTypeAudio])};
    NSData *data=[NSJSONSerialization dataWithJSONObject:report options:NSJSONWritingPrettyPrinted error:NULL];
    [data writeToFile:reportPath atomically:YES];
    [NSApp terminate:nil];
}

static void start(void) {
    AudioObjectPropertyAddress a={kAudioHardwarePropertyDevices,kAudioObjectPropertyScopeGlobal,kAudioObjectPropertyElementMain};
    UInt32 size=0;AudioObjectGetPropertyDataSize(kAudioObjectSystemObject,&a,0,NULL,&size);
    AudioObjectID *ids=malloc(size);AudioObjectGetPropertyData(kAudioObjectSystemObject,&a,0,NULL,&size,ids);
    for(unsigned i=0;i<size/sizeof(AudioObjectID);i++) {
        CFStringRef name=NULL;UInt32 len=sizeof(name);
        a=(AudioObjectPropertyAddress){kAudioObjectPropertyName,kAudioObjectPropertyScopeGlobal,kAudioObjectPropertyElementMain};
        if(!AudioObjectGetPropertyData(ids[i],&a,0,NULL,&len,&name)) {
            if([(__bridge NSString*)name isEqualToString:@"POD HD300 USB Bridge 2ch"]) device=ids[i];
            CFRelease(name);
        }
    }
    free(ids);
    if(!device) { finish(@"Virtual bridge device not found");return; }
    a=(AudioObjectPropertyAddress){kAudioDevicePropertyNominalSampleRate,kAudioObjectPropertyScopeGlobal,kAudioObjectPropertyElementMain};
    size=sizeof(rate);OSStatus err=AudioObjectGetPropertyData(device,&a,0,NULL,&size,&rate);
    if(err) { finish([NSString stringWithFormat:@"Sample rate query failed: %d",(int)err]);return; }
    err=AudioDeviceCreateIOProcID(device,io,NULL,&proc);
    if(!err) err=AudioDeviceStart(device,proc);
    if(err) { finish([NSString stringWithFormat:@"AudioDeviceStart failed: %d",(int)err]);return; }
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW,3*NSEC_PER_SEC),dispatch_get_main_queue(),^{finish(nil);});
}

@interface Delegate : NSObject<NSApplicationDelegate>
@end
@implementation Delegate
- (void)applicationDidFinishLaunching:(NSNotification*)note {
    [AVCaptureDevice requestAccessForMediaType:AVMediaTypeAudio completionHandler:^(BOOL granted){
        dispatch_async(dispatch_get_main_queue(),^{if(granted) start();else finish(@"Microphone permission denied for Audio Check");});
    }];
}
@end

int main(int argc,const char **argv) {
    @autoreleasepool {
        NSString *bundle=[[NSBundle mainBundle] bundlePath];
        captureOnly=[[NSProcessInfo processInfo].arguments containsObject:@"--capture-hd300"];
        reportPath=[[[bundle stringByDeletingLastPathComponent] stringByDeletingLastPathComponent] stringByAppendingPathComponent:captureOnly?@"logs/usb-to-hal-capture.json":@"logs/hal-native-loopback.json"];
        [NSApplication sharedApplication];
        [NSApp setActivationPolicy:NSApplicationActivationPolicyAccessory];
        Delegate *delegate=[Delegate new];NSApp.delegate=delegate;[NSApp run];
    }
    return 0;
}
