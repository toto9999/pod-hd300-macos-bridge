#import <Cocoa/Cocoa.h>

@interface Control : NSObject<NSApplicationDelegate>
@property NSWindow *window;
@property NSTextField *status,*meters,*virtualLevel,*gainLabel,*message;
@property NSLevelIndicator *meter;
@property NSPopUpButton *profile;
@property NSSlider *gain;
@property NSString *root;
@property double virtualDB;
@property NSInteger ticks;
@end

@implementation Control
- (NSTextField*)label:(NSString*)text y:(CGFloat)y size:(CGFloat)size {
    NSTextField *v=[NSTextField labelWithString:text];v.frame=NSMakeRect(24,y,548,30);
    v.font=[NSFont systemFontOfSize:size];[self.window.contentView addSubview:v];return v;
}
- (NSButton*)button:(NSString*)title action:(SEL)action x:(CGFloat)x y:(CGFloat)y width:(CGFloat)width {
    NSButton *v=[NSButton buttonWithTitle:title target:self action:action];
    v.frame=NSMakeRect(x,y,width,32);[self.window.contentView addSubview:v];return v;
}
- (NSDictionary*)readJSON:(NSString*)path {
    NSData *data=[NSData dataWithContentsOfFile:[self.root stringByAppendingPathComponent:path]];
    return data?[NSJSONSerialization JSONObjectWithData:data options:0 error:NULL]:nil;
}
- (void)applicationDidFinishLaunching:(NSNotification*)note {
    self.root=[[[NSBundle.mainBundle.bundlePath stringByDeletingLastPathComponent] stringByDeletingLastPathComponent] copy];
    self.window=[[NSWindow alloc] initWithContentRect:NSMakeRect(0,0,600,480)
        styleMask:NSWindowStyleMaskTitled|NSWindowStyleMaskClosable|NSWindowStyleMaskMiniaturizable
        backing:NSBackingStoreBuffered defer:NO];
    self.window.title=@"HD300 Control";[self.window center];
    self.window.releasedWhenClosed=NO;
    [self label:@"POD HD300 USB Bridge" y:426 size:22];
    self.status=[self label:@"연결 상태 확인 중…" y:390 size:14];
    [self button:@"시작" action:@selector(start:) x:428 y:423 width:70];
    [self button:@"중지" action:@selector(stop:) x:502 y:423 width:70];
    [self label:@"지연 설정" y:341 size:14];
    self.profile=[[NSPopUpButton alloc] initWithFrame:NSMakeRect(150,344,420,28) pullsDown:NO];
    [self.profile addItemsWithTitles:@[@"안정 · 목표 10.7 ms",@"낮은 지연 · 목표 5.3 ms",@"최소 지연 · 목표 2.7 ms"]];
    self.profile.target=self;self.profile.action=@selector(changed:);[self.window.contentView addSubview:self.profile];
    [self label:@"끊김이 감지되면 버퍼를 자동으로 늘립니다. 표시 지연은 브리지 내부 값입니다." y:310 size:11];
    self.gainLabel=[self label:@"추가 입력 증폭: 0 dB" y:264 size:14];
    self.gain=[NSSlider sliderWithValue:0 minValue:-12 maxValue:18 target:self action:@selector(changed:)];
    self.gain.frame=NSMakeRect(24,234,548,24);self.gain.continuous=YES;self.gain.numberOfTickMarks=11;
    [self.window.contentView addSubview:self.gain];
    self.virtualLevel=[self label:@"가상 장치 녹음 레벨 확인 중…" y:191 size:13];
    [self button:@"가상 입력 100% 복구…" action:@selector(unity:) x:378 y:190 width:196];
    self.meter=[[NSLevelIndicator alloc] initWithFrame:NSMakeRect(24,153,548,20)];
    self.meter.levelIndicatorStyle=NSLevelIndicatorStyleContinuousCapacity;
    self.meter.minValue=-60;self.meter.maxValue=0;self.meter.warningValue=-6;self.meter.criticalValue=-1;
    [self.window.contentView addSubview:self.meter];
    self.meters=[self label:@"입력 피크 —" y:116 size:13];
    self.message=[self label:@"처음에는 낮은 증폭으로 연주하며 조절하세요." y:78 size:12];
    [self label:@"창을 닫아도 전송은 계속됩니다. 종료하려면 중지를 누르세요." y:50 size:10];
    [self button:@"증폭 0 dB" action:@selector(zero:) x:24 y:24 width:110];
    [self button:@"폴더 열기" action:@selector(folder:) x:462 y:24 width:110];
    NSDictionary *settings=[self readJSON:@"settings.json"];
    NSArray *profiles=@[@"stable",@"low",@"minimum"];
    NSUInteger p=[profiles indexOfObject:settings[@"profile"]?:@"stable"];
    [self.profile selectItemAtIndex:p==NSNotFound?0:p];
    self.gain.doubleValue=[settings[@"gain_db"] doubleValue];
    self.gainLabel.stringValue=[NSString stringWithFormat:@"추가 입력 증폭: %+.1f dB",self.gain.doubleValue];
    self.virtualDB=0;[self tick:nil];
    [NSTimer scheduledTimerWithTimeInterval:0.25 target:self selector:@selector(tick:) userInfo:nil repeats:YES];
    [self.window makeKeyAndOrderFront:nil];[NSApp activateIgnoringOtherApps:YES];
}
- (void)changed:(id)sender {
    double gain=round(self.gain.doubleValue*2)/2;self.gain.doubleValue=gain;
    NSDictionary *settings=@{@"profile":@[@"stable",@"low",@"minimum"][self.profile.indexOfSelectedItem],@"gain_db":@(gain)};
    NSData *data=[NSJSONSerialization dataWithJSONObject:settings options:NSJSONWritingPrettyPrinted error:NULL];
    [data writeToFile:[self.root stringByAppendingPathComponent:@"settings.json"] atomically:YES];
    self.gainLabel.stringValue=[NSString stringWithFormat:@"추가 입력 증폭: %+.1f dB",gain];
}
- (NSString*)run:(NSString*)relative arguments:(NSArray*)args {
    NSTask *task=[NSTask new];task.executableURL=[NSURL fileURLWithPath:[self.root stringByAppendingPathComponent:relative]];
    task.arguments=args;task.currentDirectoryURL=[NSURL fileURLWithPath:self.root];
    NSPipe *pipe=[NSPipe pipe];task.standardOutput=pipe;task.standardError=pipe;
    NSError *error=nil;if(![task launchAndReturnError:&error]) return error.localizedDescription;
    NSData *output=[pipe.fileHandleForReading readDataToEndOfFile];[task waitUntilExit];
    return [[NSString alloc] initWithData:output encoding:NSUTF8StringEncoding]?:@"";
}
- (void)start:(id)sender {
    self.message.stringValue=@"시작하고 있습니다…";
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0),^{
        NSString *text=[self run:@".venv/bin/python" arguments:@[[self.root stringByAppendingPathComponent:@"src/start_bridge.py"]]];
        dispatch_async(dispatch_get_main_queue(),^{self.message.stringValue=[text componentsSeparatedByString:@"\n"].firstObject;});
    });
}
- (void)stop:(id)sender {
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0),^{
        NSString *text=[self run:@".venv/bin/python" arguments:@[[self.root stringByAppendingPathComponent:@"src/stop_bridge.py"]]];
        dispatch_async(dispatch_get_main_queue(),^{self.message.stringValue=[text componentsSeparatedByString:@"\n"].firstObject;});
    });
}
- (void)unity:(id)sender {
    NSAlert *alert=[NSAlert new];alert.messageText=@"입력이 크게 커질 수 있습니다";
    alert.informativeText=@"스피커·헤드폰 볼륨을 먼저 낮추거나 GarageBand 모니터링을 꺼주세요. 가상 장치만 100%로 복구하며, 스피커 볼륨은 바꾸지 않습니다.";
    [alert addButtonWithTitle:@"취소"];[alert addButtonWithTitle:@"볼륨 낮췄음 · 복구"];
    if([alert runModal]==NSAlertSecondButtonReturn) {
        NSString *text=[self run:@"build/bridge-level" arguments:@[@"--unity"]];
        [text writeToFile:[self.root stringByAppendingPathComponent:@"logs/bridge-level-restored.json"] atomically:YES encoding:NSUTF8StringEncoding error:NULL];
        self.ticks=0;[self tick:nil];
    }
}
- (void)zero:(id)sender {self.gain.doubleValue=0;[self changed:sender];}
- (void)folder:(id)sender {[NSWorkspace.sharedWorkspace openURL:[NSURL fileURLWithPath:self.root]];}
- (void)tick:(id)sender {
    if(self.ticks++%4==0) {
        NSString *text=[self run:@"build/bridge-level" arguments:@[]];
        NSDictionary *level=[NSJSONSerialization JSONObjectWithData:[text dataUsingEncoding:NSUTF8StringEncoding] options:0 error:NULL];
        if(level[@"after_scalar"]) {
            double scalar=[level[@"after_scalar"] doubleValue];self.virtualDB=-64+64*scalar;
            self.virtualLevel.stringValue=[NSString stringWithFormat:@"가상 입력 %.0f%%  (%+.1f dB)",scalar*100,self.virtualDB];
        }
    }
    NSDictionary *s=[self readJSON:@"logs/bridge-status.json"];
    BOOL fresh=s && NSDate.date.timeIntervalSince1970-[s[@"updated_at"] doubleValue]<3;
    BOOL running=fresh && [s[@"state"] isEqual:@"running"];
    double delay=[s[@"queue_delay_ms"] doubleValue];
    self.status.stringValue=running?[NSString stringWithFormat:@"연결됨 · 버퍼 %.1f ms · 끊김 %@회",delay,s[@"underruns"]?:@0]:@"입력 중지 또는 연결 대기 · 시작 버튼으로 연결";
    id value=s[@"output_meter_peak_dbfs"];
    double peak=running && [value isKindOfClass:NSNumber.class]?[value doubleValue]+self.virtualDB:-120;
    self.meter.doubleValue=fmax(-60,fmin(0,peak));
    self.meters.stringValue=peak>-110?[NSString stringWithFormat:@"예상 입력 피크 %.1f dBFS · 실제 버퍼 %@ 프레임",peak,s[@"effective_buffer_frames"]?:@0]:@"입력 피크 — · 연주하면 표시됩니다";
    if([s[@"output_overrange_samples"] unsignedLongLongValue]>0) self.message.stringValue=@"0 dBFS 초과가 감지됐습니다. 추가 증폭을 낮춰주세요.";
    else if([s[@"effective_buffer_frames"] integerValue]>[s[@"buffer_target_frames"] integerValue]) self.message.stringValue=@"안정화를 위해 버퍼를 늘렸습니다. 안정되면 다시 줄입니다.";
    else self.message.stringValue=@"현재 선택한 지연 목표로 전송 중입니다.";
}
- (BOOL)applicationShouldTerminateAfterLastWindowClosed:(NSApplication*)sender {return YES;}
@end

int main(int argc,const char **argv) {@autoreleasepool {
    [NSApplication sharedApplication];Control *delegate=[Control new];NSApp.delegate=delegate;[NSApp run];
}return 0;}
