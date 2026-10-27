#include <math.h>
#include <stdint.h>
#include <pthread/qos.h>
int hd300_usb_thread_priority(void) {
    return pthread_set_qos_class_self_np(QOS_CLASS_USER_INTERACTIVE,0);
}
// Caller owns the FIFO mutex; the audio thread allocates no memory here.
void hd300_resample(const float *ring, int capacity, int64_t read,
                    double phase, double step, const float *kernels,
                    float *output, int count) {
    for(int i=0;i<count;i++) {
        double position=phase+i*step;
        int64_t whole=(int64_t)position;
        int p=(int)((position-whole)*1024);
        int index=(int)((read+whole-15)%capacity);
        if(index<0) index+=capacity;
        const float *kernel=kernels+p*32;
        double left=0,right=0;
        for(int tap=0;tap<32;tap++) {
            left+=kernel[tap]*ring[index*2];
            right+=kernel[tap]*ring[index*2+1];
            if(++index==capacity) index=0;
        }
        output[i*2]=(float)left;
        output[i*2+1]=(float)right;
    }
}
