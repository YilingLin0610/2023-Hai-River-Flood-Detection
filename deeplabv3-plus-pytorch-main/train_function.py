
"""
This section  is used train a model
Author: Modified from https://github.com/bubbliiiing/Semantic-Segmentation/tree/master/deeplab_Mobile.
"""
import os
import datetime

import numpy as np
import torch

import torch.backends.cudnn as cudnn
import torch.distributed as dist
import torch.optim as optim
from torch.utils.data import DataLoader

from nets.deeplabv3_plus import DeepLab
from nets.deeplabv3_training import (get_lr_scheduler, set_optimizer_lr,
                                     weights_init)
from utils.callbacks import LossHistory, EvalCallback
from utils.dataloader import DeeplabDataset, deeplab_dataset_collate
from utils.utils import download_weights, show_config
from utils.utils_fit import fit_one_epoch




def train(model_path,logs_path):
    """
    train a model
    ����������������������������������������������������
    @param��
        model_path: The file path of the pretrained checkpoint.
        logs_path:
    @return:
        None
    """





    # ---------------------------------#
    #   Cuda    �Ƿ�ʹ��Cuda
    #           û��GPU�������ó�False
    # ---------------------------------#
    Cuda = True
    # ---------------------------------------------------------------------#
    #   distributed     ����ָ���Ƿ�ʹ�õ����࿨�ֲ�ʽ����
    #                   �ն�ָ���֧��Ubuntu��CUDA_VISIBLE_DEVICES������Ubuntu��ָ���Կ���
    #                   Windowsϵͳ��Ĭ��ʹ��DPģʽ���������Կ�����֧��DDP��
    #   DPģʽ��
    #       ����            distributed = False
    #       ���ն�������    CUDA_VISIBLE_DEVICES=0,1 python train.py
    #   DDPģʽ��
    #       ����            distributed = True
    #       ���ն�������    CUDA_VISIBLE_DEVICES=0,1 python -m torch.distributed.launch --nproc_per_node=2 train.py
    # ---------------------------------------------------------------------#
    distributed = True
    # ---------------------------------------------------------------------#
    #   sync_bn     �Ƿ�ʹ��sync_bn��DDPģʽ�࿨����
    # ---------------------------------------------------------------------#
    sync_bn = False
    # ---------------------------------------------------------------------#
    #   fp16        �Ƿ�ʹ�û�Ͼ���ѵ��
    #               �ɼ���Լһ����Դ桢��Ҫpytorch1.7.1����
    # ---------------------------------------------------------------------#
    fp16 = False
    # -----------------------------------------------------#
    #   num_classes     ѵ���Լ������ݼ�����Ҫ�޸ĵ�
    #                   �Լ���Ҫ�ķ������+1����2+1
    # -----------------------------------------------------#
    #   ��ʹ�õĵ��������磺
    #   mobilenet
    #   xception
    # ---------------------------------#
    backbone = "mobilenet"
    # ----------------------------------------------------------------------------------------------------------------------------#
    #   pretrained      �Ƿ�ʹ�����������Ԥѵ��Ȩ�أ��˴�ʹ�õ������ɵ�Ȩ�أ��������ģ�͹�����ʱ����м��صġ�
    #                   ���������mtmodel_pah�������ɵ�Ȩֵ������أ�pretrained��ֵ�����塣
    #                   ���������model_path��pretrained = True����ʱ���������ɿ�ʼѵ����
    #                   ���������odel_path��pretrained = False��Freeze_Train = Fasle����ʱ��0��ʼѵ������û�ж������ɵĹ��̡�
    # ----------------------------------------------------------------------------------------------------------------------------#
    pretrained = False
    # ----------------------------------------------------------------------------------------------------------------------------#
    #   Ȩֵ�ļ��������뿴README������ͨ���������ء�ģ�͵� Ԥѵ��Ȩ�� �Բ�ͬ���ݼ���ͨ�õģ���Ϊ������ͨ�õġ�
    #   ģ�͵� Ԥѵ��Ȩ�� �Ƚ���Ҫ�Ĳ����� ����������ȡ�����Ȩֵ���֣����ڽ���������ȡ��
    #   Ԥѵ��Ȩ�ض���99%�����������Ҫ�ã����õĻ����ɲ��ֵ�Ȩֵ̫�������������ȡЧ�������ԣ�����ѵ���Ľ��Ҳ�����
    #   ѵ���Լ������ݼ�ʱ��ʾά�Ȳ�ƥ��������Ԥ��Ķ�������һ������Ȼά�Ȳ�ƥ��
    #
    #   ���ѵ�������д����ж�ѵ���Ĳ��������Խ�model_path���ó�logs�ļ����µ�Ȩֵ�ļ������Ѿ�ѵ����һ���ֵ�Ȩֵ�ٴ����롣
    #   ͬʱ�޸��·��� ����׶� ���� �ⶳ�׶� �Ĳ���������֤ģ��epoch�������ԡ�
    #
    #   ��model_path = ''��ʱ�򲻼�������ģ�͵�Ȩֵ��
    #
    #   �˴�ʹ�õ�������ģ�͵�Ȩ�أ��������train.py���м��صģ�pretrain��Ӱ��˴���Ȩֵ���ء�
    #   �����Ҫ��ģ�ʹ����ɵ�Ԥѵ��Ȩֵ��ʼѵ����������model_path = ''��pretrain = True����ʱ���������ɡ�
    #   �����Ҫ��ģ�ʹ�0��ʼѵ����������model_path = ''��pretrain = Fasle��Freeze_Train = Fasle����ʱ��0��ʼѵ������û�ж������ɵĹ��̡�
    #
    #   һ�������������0��ʼ��ѵ��Ч����ܲ��ΪȨֵ̫�������������ȡЧ�������ԣ���˷ǳ����ǳ����ǳ��������Ҵ�0��ʼѵ����
    #   ���һ��Ҫ��0��ʼ�������˽�imagenet���ݼ�������ѵ������ģ�ͣ������������ɲ���Ȩֵ������ģ�͵� ���ɲ��� �͸�ģ��ͨ�ã����ڴ˽���ѵ����
    # ----------------------------------------------------------------------------------------------------------------------------#
    # model_path      = r"/root/autodl-tmp/project/deeplabv3-plus-pytorch-main/logs/2021_finetunning_0.2_fixed_nonRTS/ep165-loss0.021-val_loss0.022.pth"
    #model_path = r"/root/autodl-tmp/project/deeplabv3-plus-pytorch-main/model_data/2019_best_epoch_weights.pth"
    # ---------------------------------------------------------#
    #   downsample_factor   �²����ı���8��16
    #                       8�²����ı�����С��������Ч�����á�
    #                       ��ҲҪ�������Դ�
    # ---------------------------------------------------------#
    downsample_factor = 16
    # ------------------------------#
    #   ����ͼƬ�Ĵ�С
    # ------------------------------#
    input_shape = [512, 512]
    num_classes=3
    # ----------------------------------------------------------------------------------------------------------------------------#
    #   ѵ����Ϊ�����׶Σ��ֱ��Ƕ���׶κͽⶳ�׶Ρ����ö���׶���Ϊ������������ܲ����ͬѧ��ѵ������
    #   ����ѵ����Ҫ���Դ��С���Կ��ǳ��������£�������Freeze_Epoch����UnFreeze_Epoch����ʱ�������ж���ѵ����
    #
    #   �ڴ��ṩ���ɲ������ý��飬��λѵ���߸����Լ������������������
    #   ��һ��������ģ�͵�Ԥѵ��Ȩ�ؿ�ʼѵ����
    #       Adam��
    #           Init_Epoch = 0��Freeze_Epoch = 50��UnFreeze_Epoch = 100��Freeze_Train = True��optimizer_type = 'adam'��Init_lr = 5e-4��weight_decay = 0�������ᣩ
    #           Init_Epoch = 0��UnFreeze_Epoch = 100��Freeze_Train = False��optimizer_type = 'adam'��Init_lr = 5e-4��weight_decay = 0���������ᣩ
    #       SGD��
    #           Init_Epoch = 0��Freeze_Epoch = 50��UnFreeze_Epoch = 100��Freeze_Train = True��optimizer_type = 'sgd'��Init_lr = 7e-3��weight_decay = 1e-4�������ᣩ
    #           Init_Epoch = 0��UnFreeze_Epoch = 100��Freeze_Train = False��optimizer_type = 'sgd'��Init_lr = 7e-3��weight_decay = 1e-4���������ᣩ
    #       ���У�UnFreeze_Epoch������100-300֮�������
    #   �����������������Ԥѵ��Ȩ�ؿ�ʼѵ����
    #       Adam��
    #           Init_Epoch = 0��Freeze_Epoch = 50��UnFreeze_Epoch = 100��Freeze_Train = True��optimizer_type = 'adam'��Init_lr = 5e-4��weight_decay = 0�������ᣩ
    #           Init_Epoch = 0��UnFreeze_Epoch = 100��Freeze_Train = False��optimizer_type = 'adam'��Init_lr = 5e-4��weight_decay = 0���������ᣩ
    #       SGD��
    #           Init_Epoch = 0��Freeze_Epoch = 50��UnFreeze_Epoch = 120��Freeze_Train = True��optimizer_type = 'sgd'��Init_lr = 7e-3��weight_decay = 1e-4�������ᣩ
    #           Init_Epoch = 0��UnFreeze_Epoch = 120��Freeze_Train = False��optimizer_type = 'sgd'��Init_lr = 7e-3��weight_decay = 1e-4���������ᣩ
    #       ���У����ڴ����������Ԥѵ��Ȩ�ؿ�ʼѵ�������ɵ�Ȩֵ��һ���ʺ�����ָ��Ҫ�����ѵ�������ֲ����Ž⡣
    #             UnFreeze_Epoch������120-300֮�������
    #             Adam�����SGD�����Ŀ�һЩ�����UnFreeze_Epoch�����Ͽ���Сһ�㣬����Ȼ�Ƽ������Epoch��
    #   ������batch_size�����ã�
    #       ���Կ��ܹ����ܵķ�Χ�ڣ��Դ�Ϊ�á��Դ治�������ݼ���С�޹أ���ʾ�Դ治�㣨OOM����CUDA out of memory�����Сbatch_size��
    #       �ܵ�BatchNorm��Ӱ�죬batch_size��СΪ2������Ϊ1��
    #       ���������Freeze_batch_size����ΪUnfreeze_batch_size��1-2�������������õĲ�������Ϊ��ϵ��ѧϰ�ʵ��Զ�������
    # ----------------------------------------------------------------------------------------------------------------------------#
    # ------------------------------------------------------------------#
    #   ����׶�ѵ������
    #   ��ʱģ�͵����ɱ������ˣ�������ȡ���粻�����ı�
    #   ռ�õ��Դ��С�������������΢��
    #   Init_Epoch          ģ�͵�ǰ��ʼ��ѵ����������ֵ���Դ���Freeze_Epoch�������ã�
    #                       Init_Epoch = 60��Freeze_Epoch = 50��UnFreeze_Epoch = 100
    #                       ����������׶Σ�ֱ�Ӵ�60����ʼ����������Ӧ��ѧϰ�ʡ�
    #                       ���ϵ�����ʱʹ�ã�
    #   Freeze_Epoch        ģ�Ͷ���ѵ����Freeze_Epoch
    #                       (��Freeze_Train=FalseʱʧЧ)
    #   Freeze_batch_size   ģ�Ͷ���ѵ����batch_size
    #                       (��Freeze_Train=FalseʱʧЧ)
    # ------------------------------------------------------------------#
    Init_Epoch =0
    Freeze_Epoch = 50
    Freeze_batch_size = 8
    # ------------------------------------------------------------------#
    #   �ⶳ�׶�ѵ������
    #   ��ʱģ
    #    �͵����ɲ��������ˣ���
    #   ����ȡ����ᷢ���ı�
    #   ռ�õ��Դ�ϴ��������еĲ������ᷢ���ı�
    #   UnFreeze_Epoch          ģ���ܹ�ѵ����epoch
    #   Unfreeze_batch_size     ģ���ڽⶳ���batch_size
    # ------------------------------------------------------------------#
    UnFreeze_Epoch = 250
    Unfreeze_batch_size = 4
    # ------------------------------------------------------------------#
    #   Freeze_Train    �Ƿ���ж���ѵ��
    #                   Ĭ���ȶ�������ѵ����ⶳѵ����
    # ------------------------------------------------------------------#
    Freeze_Train = True

    # ------------------------------------------------------------------#
    #   ����ѵ��������ѧϰ�ʡ��Ż�����ѧϰ���½��й�
    # ------------------------------------------------------------------#
    # ------------------------------------------------------------------#
    #   Init_lr         ģ�͵����ѧϰ��
    #                   ��ʹ��Adam�Ż���ʱ��������  Init_lr=5e-4
    #                   ��ʹ��SGD�Ż���ʱ��������   Init_lr=7e-3
    #   Min_lr          ģ�͵���Сѧϰ�ʣ�Ĭ��Ϊ���ѧϰ�ʵ�0.01
    # ------------------------------------------------------------------#
    Init_lr = 7e-3
    Min_lr = 7e-3 * 0.01
    # ------------------------------------------------------------------#
    #   optimizer_type  ʹ�õ����Ż������࣬��ѡ����adam��sgd
    #                   ��ʹ��Adam�Ż���ʱ��������  Init_lr=5e-4
    #                   ��ʹ��SGD�Ż���ʱ��������   Init_lr=7e-3
    #   momentum        �Ż����ڲ�ʹ�õ���momentum����
    #   weight_decay    Ȩֵ˥�����ɷ�ֹ�����
    #                   adam�ᵼ��weight_decay����ʹ��adamʱ��������Ϊ0��
    # ------------------------------------------------------------------#
    optimizer_type = "sgd"
    momentum = 0.9
    weight_decay = 1e-4
    # ------------------------------------------------------------------#
    #   lr_decay_type   ʹ�õ���ѧϰ���½���ʽ����ѡ����'step'��'cos'
    # ------------------------------------------------------------------#
    lr_decay_type = 'cos'
    # ------------------------------------------------------------------#
    #   save_period     ���ٸ�epoch����һ��Ȩֵ
    # ------------------------------------------------------------------#
    save_period = 100
    # ------------------------------------------------------------------#
    #   save_dir        Ȩֵ����־�ļ�������ļ���
    # ------------------------------------------------------------------#
    save_dir = r''
    # ------------------------------------------------------------------#
    #   eval_flag       �Ƿ���ѵ��ʱ������������������Ϊ��֤��
    #   eval_period     ������ٸ�epoch����һ�Σ�������Ƶ��������
    #                   ������Ҫ���Ľ϶��ʱ�䣬Ƶ�������ᵼ��ѵ���ǳ���
    #   �˴���õ�mAP����get_map.py��õĻ�������ͬ��ԭ���ж���
    #   ��һ���˴���õ�mAPΪ��֤����mAP��
    #   �������˴���������������Ϊ���أ�Ŀ���Ǽӿ������ٶȡ�
    # ------------------------------------------------------------------#
    eval_flag = True
    eval_period = 5

    # ------------------------------------------------------------------#
    #   VOCdevkit_path  ���ݼ�·��
    # ------------------------------------------------------------------#
    VOCdevkit_path = 'RTS_datas'
    # ------------------------------------------------------------------#
    #   ����ѡ�
    #   �����٣����ࣩʱ������ΪTrue
    #   ����ࣨʮ���ࣩʱ�����batch_size�Ƚϴ�10���ϣ�����ô����ΪTrue
    #   ����ࣨʮ���ࣩʱ�����batch_size�Ƚ�С��10���£�����ô����ΪFalse
    # ------------------------------------------------------------------#
    dice_loss = False
    # ------------------------------------------------------------------#
    #   �Ƿ�ʹ��focal loss����ֹ����������ƽ��
    # ------------------------------------------------------------------#
    focal_loss = False
    # ------------------------------------------------------------------#
    #   �Ƿ����ͬ���ำ�費ͬ����ʧȨֵ��Ĭ����ƽ��ġ�
    #   ���õĻ���ע�����ó�numpy��ʽ�ģ����Ⱥ�num_classesһ����
    #   �磺
    #   num_classes = 3
    #   cls_weights = np.array([1, 2, 3], np.float32)
    # ------------------------------------------------------------------#
    # cls_weights = np.array([1, 2, 3], np.float32)
    cls_weights = np.ones([num_classes], np.float32)
    # ------------------------------------------------------------------#
    #   num_workers     ���������Ƿ�ʹ�ö��̶߳�ȡ���ݣ�1����رն��߳�
    #                   �������ӿ����ݶ�ȡ�ٶȣ����ǻ�ռ�ø����ڴ�
    #                   keras�￪�����߳���Щʱ���ٶȷ����������
    #                   ��IOΪƿ����ʱ���ٿ������̣߳���GPU�����ٶ�Զ���ڶ�ȡͼƬ���ٶȡ�
    # ------------------------------------------------------------------#
    num_workers = 4

    # ------------------------------------------------------#
    #   �����õ����Կ�
    # ------------------------------------------------------#
    ngpus_per_node = torch.cuda.device_count()
    if distributed:
        dist.init_process_group(backend="nccl")
        local_rank = int(os.environ["LOCAL_RANK"])
        rank = int(os.environ["RANK"])
        device = torch.device("cuda", local_rank)
        if local_rank == 0:
            print(f"[{os.getpid()}] (rank = {rank}, local_rank = {local_rank}) training...")
            print("Gpu Device Count : ", ngpus_per_node)
    else:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        local_rank = 0

    # ----------------------------------------------------#
    #   ����Ԥѵ��Ȩ��
    # ----------------------------------------------------#
    if pretrained:
        if distributed:
            if local_rank == 0:
                download_weights(backbone)
            dist.barrier()
        else:
            download_weights(backbone)
    print("yes")

    model = DeepLab(num_classes=num_classes, backbone=backbone, downsample_factor=downsample_factor,
                    pretrained=pretrained)
    if not pretrained:
        weights_init(model)
    if model_path != '':
        # ------------------------------------------------------#
        #   Ȩֵ�ļ��뿴README���ٶ���������
        # ------------------------------------------------------#
        if local_rank == 0:
            print('Load weights {}.'.format(model_path))

        # ------------------------------------------------------#
        #   ����Ԥѵ��Ȩ�ص�Key��ģ�͵�Key���м���
        # ------------------------------------------------------#
        model_dict = model.state_dict()
        # pretrained_dict = torch.load(model_path, map_location = 'cuda:0')

        pretrained_dict = torch.load(model_path, map_location=device)
        load_key, no_load_key, temp_dict = [], [], {}
        for k, v in pretrained_dict.items():
            if k in model_dict.keys() and np.shape(model_dict[k]) == np.shape(v):
                temp_dict[k] = v
                load_key.append(k)
            else:
                no_load_key.append(k)
        model_dict.update(temp_dict)
        model.load_state_dict(model_dict)
        # ------------------------------------------------------#
        #   ��ʾû��ƥ���ϵ�Key
        # ------------------------------------------------------#
        if local_rank == 0:
            print("\nSuccessful Load Key:", str(load_key)[:500], "����\nSuccessful Load Key Num:", len(load_key))
            print("\nFail To Load Key:", str(no_load_key)[:500], "����\nFail To Load Key num:", len(no_load_key))
            print("\n\033[1;33;44m��ܰ��ʾ��head����û����������������Backbone����û�������Ǵ���ġ�\033[0m")

    # ----------------------#
    #   ��¼Loss
    # ----------------------#
    if local_rank == 0:
        # time_str        = datetime.dat1et
        # ime.strftime(datetime.datetime.now(),'%Y_%m_%d_%H_%M_%S')
        log_dir = os.path.join(save_dir, logs_path)
        save_dir = log_dir
        loss_history = LossHistory(log_dir, model, input_shape=input_shape)
    else:
        loss_history = None

    # ------------------------------------------------------------------#
    #   torch 1.2��֧��amp������ʹ��torch 1.7.1��������ȷʹ��fp16
    #   ���torch1.2������ʾ"could not be resolve"
    # ------------------------------------------------------------------#
    if fp16:
        from torch.cuda.amp import GradScaler as GradScaler
        scaler = GradScaler()
    else:
        scaler = None

    model_train = model.train()
    # ----------------------------#
    #   �࿨ͬ��Bn
    # ----------------------------#
    if sync_bn and ngpus_per_node > 1 and distributed:
        model_train = torch.nn.SyncBatchNorm.convert_sync_batchnorm(model_train)
    elif sync_bn:
        print("Sync_bn is not support in one gpu or not distributed.")

    if Cuda:
        if distributed:
            # ----------------------------#
            #   �࿨ƽ������
            # ----------------------------#
            model_train = model_train.cuda(local_rank)
            model_train = torch.nn.parallel.DistributedDataParallel(model_train, device_ids=[local_rank],
                                                                    find_unused_parameters=True)
        else:
            model_train = torch.nn.DataParallel(model)
            cudnn.benchmark = True
            model_train = model_train.cuda()

    # ---------------------------#
    #   ��ȡ���ݼ���Ӧ��txt
    # ---------------------------#
    with open(os.path.join(VOCdevkit_path, "RTS_datasets/ImageSets/Segmentation/train.txt"), "r") as f:
        train_lines = f.readlines()
    with open(os.path.join(VOCdevkit_path, "RTS_datasets/ImageSets/Segmentation/val.txt"), "r") as f:
        val_lines = f.readlines()
    num_train = len(train_lines)
    num_val = len(val_lines)
    # չʾģ������
    if local_rank == 0:
        show_config(
            num_classes=num_classes, backbone=backbone, model_path=model_path, input_shape=input_shape, \
            Init_Epoch=Init_Epoch, Freeze_Epoch=Freeze_Epoch, UnFreeze_Epoch=UnFreeze_Epoch,
            Freeze_batch_size=Freeze_batch_size, Unfreeze_batch_size=Unfreeze_batch_size, Freeze_Train=Freeze_Train, \
            Init_lr=Init_lr, Min_lr=Min_lr, optimizer_type=optimizer_type, momentum=momentum,
            lr_decay_type=lr_decay_type, \
            save_period=save_period, save_dir=save_dir, num_workers=num_workers, num_train=num_train, num_val=num_val
        )
        # ---------------------------------------------------------#
        #   ��ѵ������ָ���Ǳ���ȫ�����ݵ��ܴ���
        #   ��ѵ������ָ�����ݶ��½����ܴ���
        #   ÿ��ѵ��������������ѵ��������ÿ��ѵ����������һ���ݶ��½���
        #   �˴����������ѵ���������ϲ��ⶥ������ʱֻ�����˽ⶳ����
        # ----------------------------------------------------------#
        wanted_step = 1.5e4 if optimizer_type == "sgd" else 0.5e4
        total_step = num_train // Unfreeze_batch_size * UnFreeze_Epoch
        if total_step <= wanted_step:
            if num_train // Unfreeze_batch_size == 0:
                raise ValueError('���ݼ���С���޷�����ѵ�������������ݼ���')
            wanted_epoch = wanted_step // (num_train // Unfreeze_batch_size) + 1
            print("\n\033[1;33;44m[Warning] ʹ��%s�Ż���ʱ�����齫ѵ���ܲ������õ�%d���ϡ�\033[0m" % (
            optimizer_type, wanted_step))
            print(
                "\033[1;33;44m[Warning] �������е���ѵ��������Ϊ%d��Unfreeze_batch_sizeΪ%d����ѵ��%d��Epoch���������ѵ������Ϊ%d��\033[0m" % (
                num_train, Unfreeze_batch_size, UnFreeze_Epoch, total_step))
            print("\033[1;33;44m[Warning] ������ѵ������Ϊ%d��С�ڽ����ܲ���%d����������������Ϊ%d��\033[0m" % (
            total_step, wanted_step, wanted_epoch))

    # ------------------------------------------------------#
    #   ����������ȡ��������ͨ�ã�����ѵ�����Լӿ�ѵ���ٶ�
    #   Ҳ������ѵ�����ڷ�ֹȨֵ���ƻ���
    #   Init_EpochΪ��ʼ����
    #   Interval_EpochΪ����ѵ��������
    #   Epoch��ѵ������
    #   ��ʾOOM�����Դ治�����СBatch_size
    # ------------------------------------------------------#
    if True:
        UnFreeze_flag = False
        # ------------------------------------#
        #   ����һ������ѵ��
        # ------------------------------------#
        if Freeze_Train:
            for param in model.backbone.parameters():
                param.requires_grad = False

        # -------------------------------------------------------------------#
        #   ���������ѵ���Ļ���ֱ������batch_sizeΪUnfreeze_batch_size
        # -------------------------------------------------------------------#
        batch_size = Freeze_batch_size if Freeze_Train else Unfreeze_batch_size

        # -------------------------------------------------------------------#
        #   �жϵ�ǰbatch_size������Ӧ����ѧϰ��
        # -------------------------------------------------------------------#
        nbs = 16
        lr_limit_max = 5e-4 if optimizer_type == 'adam' else 1e-1
        lr_limit_min = 3e-4 if optimizer_type == 'adam' else 5e-4
        if backbone == "xception":
            lr_limit_max = 1e-4 if optimizer_type == 'adam' else 1e-1
            lr_limit_min = 1e-4 if optimizer_type == 'adam' else 5e-4
        Init_lr_fit = min(max(batch_size / nbs * Init_lr, lr_limit_min), lr_limit_max)
        Min_lr_fit = min(max(batch_size / nbs * Min_lr, lr_limit_min * 1e-2), lr_limit_max * 1e-2)

        # ---------------------------------------#
        #   ����optimizer_typeѡ���Ż���
        # ---------------------------------------#
        optimizer = {
            'adam': optim.Adam(model.parameters(), Init_lr_fit, betas=(momentum, 0.999), weight_decay=weight_decay),
            'sgd': optim.SGD(model.parameters(), Init_lr_fit, momentum=momentum, nesterov=True,
                             weight_decay=weight_decay)
        }[optimizer_type]

        # ---------------------------------------#
        #   ���ѧϰ���½��Ĺ�ʽ
        # ---------------------------------------#
        lr_scheduler_func = get_lr_scheduler(lr_decay_type, Init_lr_fit, Min_lr_fit, UnFreeze_Epoch)

        # ---------------------------------------#
        #   �ж�ÿһ�������ĳ���
        # ---------------------------------------#
        epoch_step = num_train // batch_size
        epoch_step_val = num_val // batch_size

        if epoch_step == 0 or epoch_step_val == 0:
            raise ValueError("���ݼ���С���޷���������ѵ�������������ݼ���")

        train_dataset = DeeplabDataset(train_lines, input_shape, num_classes, True, VOCdevkit_path)
        val_dataset = DeeplabDataset(val_lines, input_shape, num_classes, False, VOCdevkit_path)

        if distributed:
            # �ֲ�ʽѵ��
            train_sampler = torch.utils.data.distributed.DistributedSampler(train_dataset, shuffle=True, )
            val_sampler = torch.utils.data.distributed.DistributedSampler(val_dataset, shuffle=False, )
            batch_size = batch_size // ngpus_per_node
            shuffle = False
        else:
            train_sampler = None
            val_sampler = None
            shuffle = True
        # ��������
        gen = DataLoader(train_dataset, shuffle=shuffle, batch_size=batch_size, num_workers=num_workers,
                         pin_memory=True,
                         drop_last=True, collate_fn=deeplab_dataset_collate, sampler=train_sampler)
        gen_val = DataLoader(val_dataset, shuffle=shuffle, batch_size=batch_size, num_workers=num_workers,
                             pin_memory=True,
                             drop_last=True, collate_fn=deeplab_dataset_collate, sampler=val_sampler)

        # ----------------------#
        #   ��¼eval��map����
        # ----------------------#
        if local_rank == 0:
            eval_callback = EvalCallback(model, input_shape, num_classes, val_lines, VOCdevkit_path, log_dir, Cuda, \
                                         eval_flag=eval_flag, period=eval_period)
        else:
            eval_callback = None

        # ---------------------------------------#
        #   ��ʼģ��ѵ��
        # ---------------------------------------#
        for epoch in range(Init_Epoch, UnFreeze_Epoch):
            # ---------------------------------------#
            #   ���ģ���ж���ѧϰ����
            #   ��ⶳ�������ò���
            # ---------------------------------------#
            if epoch >= Freeze_Epoch and not UnFreeze_flag and Freeze_Train:
                batch_size = Unfreeze_batch_size

                # -------------------------------------------------------------------#
                #   �жϵ�ǰbatch_size������Ӧ����ѧϰ��
                # -------------------------------------------------------------------#
                nbs = 16
                lr_limit_max = 5e-4 if optimizer_type == 'adam' else 1e-1
                lr_limit_min = 3e-4 if optimizer_type == 'adam' else 5e-4
                if backbone == "xception":
                    lr_limit_max = 1e-4 if optimizer_type == 'adam' else 1e-1
                    lr_limit_min = 1e-4 if optimizer_type == 'adam' else 5e-4
                Init_lr_fit = min(max(batch_size / nbs * Init_lr, lr_limit_min), lr_limit_max)
                Min_lr_fit = min(max(batch_size / nbs * Min_lr, lr_limit_min * 1e-2), lr_limit_max * 1e-2)
                # ---------------------------------------#
                #   ���ѧϰ���½��Ĺ�ʽ
                # ---------------------------------------#
                lr_scheduler_func = get_lr_scheduler(lr_decay_type, Init_lr_fit, Min_lr_fit, UnFreeze_Epoch)

                for param in model.backbone.parameters():
                    param.requires_grad = True

                epoch_step = num_train // batch_size
                epoch_step_val = num_val // batch_size

                if epoch_step == 0 or epoch_step_val == 0:
                    raise ValueError("���ݼ���С���޷���������ѵ�������������ݼ���")

                if distributed:
                    batch_size = batch_size // ngpus_per_node

                gen = DataLoader(train_dataset, shuffle=shuffle, batch_size=batch_size, num_workers=num_workers,
                                 pin_memory=True,
                                 drop_last=True, collate_fn=deeplab_dataset_collate, sampler=train_sampler)
                gen_val = DataLoader(val_dataset, shuffle=shuffle, batch_size=batch_size, num_workers=num_workers,
                                     pin_memory=True,
                                     drop_last=True, collate_fn=deeplab_dataset_collate, sampler=val_sampler)

                UnFreeze_flag = True

            if distributed:
                train_sampler.set_epoch(epoch)

            set_optimizer_lr(optimizer, lr_scheduler_func, epoch)

            fit_one_epoch(model_train, model, loss_history, eval_callback, optimizer, epoch,
                          epoch_step, epoch_step_val, gen, gen_val, UnFreeze_Epoch, Cuda, dice_loss, focal_loss,
                          cls_weights, num_classes, fp16, scaler, save_period, save_dir, local_rank)

            if distributed:
                dist.barrier()

        if local_rank == 0:
            loss_history.writer.close()
